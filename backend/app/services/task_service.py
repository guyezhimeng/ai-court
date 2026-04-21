import enum
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import (
    Task, TaskState, TaskTransition,
    STATE_TRANSITIONS, STATE_AGENT_MAP, ORG_AGENT_MAP,
)
from app.models.outbox import OutboxEvent
from app.services.event_bus import (
    TOPIC_TASK_STATUS, TOPIC_TASK_DISPATCH, TOPIC_TASK_COMPLETED,
    TOPIC_TASK_STALLED, TOPIC_TASK_ESCALATED,
)

logger = logging.getLogger(__name__)


class TaskService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_task(
        self,
        title: str,
        description: str = "",
        session_id: str | None = None,
        priority: str = "normal",
        metadata: dict | None = None,
    ) -> Task:
        trace_id = f"JJC-{uuid.uuid4().hex[:8].upper()}"
        task = Task(
            trace_id=trace_id,
            title=title,
            description=description,
            state=TaskState.Taizi,
            priority=priority,
            session_id=uuid.UUID(session_id) if session_id else None,
            metadata_=metadata or {},
        )
        self.db.add(task)

        outbox = OutboxEvent(
            topic=TOPIC_TASK_STATUS,
            trace_id=trace_id,
            event_type="task.created",
            payload={"task_id": str(task.id), "trace_id": trace_id, "state": "Taizi"},
        )
        self.db.add(outbox)

        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def get_task(self, task_id: str) -> Task | None:
        result = await self.db.execute(
            select(Task).where(Task.id == uuid.UUID(task_id))
        )
        return result.scalar_one_or_none()

    async def get_task_by_trace(self, trace_id: str) -> Task | None:
        result = await self.db.execute(
            select(Task).where(Task.trace_id == trace_id)
        )
        return result.scalar_one_or_none()

    async def list_tasks(
        self,
        state: TaskState | None = None,
        is_archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Task]:
        query = select(Task).where(Task.is_archived == is_archived)
        if state:
            query = query.where(Task.state == state)
        query = query.order_by(Task.updated_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def transition_state(
        self,
        task_id: str,
        new_state: TaskState,
        agent_id: str | None = None,
        comment: str = "",
    ) -> Task:
        task = await self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        old_state = task.state
        allowed = STATE_TRANSITIONS.get(old_state, set())
        if new_state not in allowed:
            raise ValueError(
                f"Invalid transition: {old_state.value} -> {new_state.value}. "
                f"Allowed: {[s.value for s in allowed]}"
            )

        transition = TaskTransition(
            task_id=task.id,
            from_state=old_state,
            to_state=new_state,
            agent_id=agent_id,
            comment=comment,
        )
        self.db.add(transition)

        task.state = new_state
        task.updated_at = datetime.now(timezone.utc)
        if new_state == TaskState.Done:
            task.completed_at = datetime.now(timezone.utc)

        outbox = OutboxEvent(
            topic=TOPIC_TASK_STATUS,
            trace_id=task.trace_id,
            event_type="task.state_changed",
            payload={
                "task_id": str(task.id),
                "trace_id": task.trace_id,
                "from_state": old_state.value,
                "to_state": new_state.value,
                "agent_id": agent_id,
                "comment": comment,
            },
        )
        self.db.add(outbox)

        if new_state == TaskState.Done:
            done_outbox = OutboxEvent(
                topic=TOPIC_TASK_COMPLETED,
                trace_id=task.trace_id,
                event_type="task.completed",
                payload={"task_id": str(task.id), "trace_id": task.trace_id},
            )
            self.db.add(done_outbox)

        await self.db.commit()
        await self.db.refresh(task)

        logger.info(f"Task {task.trace_id}: {old_state.value} -> {new_state.value}")
        return task

    async def request_dispatch(
        self, task_id: str, agent_id: str, message: str = ""
    ) -> None:
        task = await self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        outbox = OutboxEvent(
            topic=TOPIC_TASK_DISPATCH,
            trace_id=task.trace_id,
            event_type="task.dispatch",
            payload={
                "task_id": str(task.id),
                "trace_id": task.trace_id,
                "agent_id": agent_id,
                "state": task.state.value,
                "message": message or task.description,
            },
        )
        self.db.add(outbox)
        await self.db.commit()

    async def update_task_summary(
        self, task_id: str, summary: str, agent_id: str | None = None
    ) -> Task:
        task = await self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        task.now_summary = summary
        task.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def update_subtasks(
        self, task_id: str, subtasks: list[dict]
    ) -> Task:
        task = await self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        task.subtasks = subtasks
        task.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def archive_task(self, task_id: str) -> Task:
        task = await self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        task.is_archived = True
        task.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def mark_stalled(self, task_id: str) -> Task:
        task = await self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        task.stall_count = (task.stall_count or 0) + 1
        task.updated_at = datetime.now(timezone.utc)

        outbox = OutboxEvent(
            topic=TOPIC_TASK_STALLED,
            trace_id=task.trace_id,
            event_type="task.stalled",
            payload={
                "task_id": str(task.id),
                "trace_id": task.trace_id,
                "stall_count": task.stall_count,
                "state": task.state.value,
            },
        )
        self.db.add(outbox)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def get_agent_for_state(self, state: TaskState) -> str | None:
        return STATE_AGENT_MAP.get(state)

    async def get_agent_for_department(self, dept: str) -> str | None:
        return ORG_AGENT_MAP.get(dept)
