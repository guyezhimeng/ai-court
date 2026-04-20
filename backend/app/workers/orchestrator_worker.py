import asyncio
import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import select

from app.db import async_session
from app.models.task import Task, TaskState
from app.models.outbox import OutboxEvent
from app.services.event_bus import (
    EventBus, get_event_bus,
    TOPIC_TASK_CREATED, TOPIC_TASK_STATUS,
    TOPIC_TASK_COMPLETED, TOPIC_TASK_STALLED,
    TOPIC_TASK_DISPATCH,
)
from app.services.task_service import TaskService

logger = logging.getLogger(__name__)

GROUP = "orchestrator"
CONSUMER = "orch-1"
MAX_STALL_RETRIES = 2

_ESCALATION_PATH = {
    TaskState.Doing: TaskState.Assigned,
    TaskState.Assigned: TaskState.Menxia,
    TaskState.Menxia: TaskState.Zhongshu,
    TaskState.Zhongshu: TaskState.Taizi,
}

WATCHED_TOPICS = [
    TOPIC_TASK_CREATED,
    TOPIC_TASK_STATUS,
    TOPIC_TASK_COMPLETED,
    TOPIC_TASK_STALLED,
]


class OrchestratorWorker:
    def __init__(self):
        self.bus: EventBus | None = None
        self._running = False

    async def start(self):
        self.bus = await get_event_bus()
        self._running = True
        logger.info("OrchestratorWorker started")

        await asyncio.gather(
            self._consume_loop(),
            self._stall_detector_loop(),
        )

    async def stop(self):
        self._running = False

    async def _consume_loop(self):
        while self._running:
            try:
                events = await self.bus.consume(
                    WATCHED_TOPICS, GROUP, CONSUMER, count=10, block_ms=3000
                )
                for event in events:
                    await self._handle_event(event)
                    stream = event.get("_stream", "")
                    msg_id = event.get("_msg_id", "")
                    topic = event.get("topic", "")
                    await self.bus.ack(GROUP, topic, msg_id)
            except Exception as e:
                logger.error(f"Orchestrator consume error: {e}")
                await asyncio.sleep(5)

    async def _handle_event(self, event: dict):
        event_type = event.get("event_type", "")
        payload = event.get("payload", {})
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                return

        if event_type == "task.created":
            await self._on_task_created(payload)
        elif event_type == "task.state_changed":
            await self._on_state_changed(payload)
        elif event_type == "task.stalled":
            await self._on_stalled(payload)

    async def _on_task_created(self, payload: dict):
        task_id = payload.get("task_id")
        if not task_id:
            return
        logger.info(f"New task created: {task_id}, dispatching to taizi")
        await self.bus.publish(
            TOPIC_TASK_DISPATCH,
            trace_id=payload.get("trace_id", ""),
            event_type="task.dispatch",
            producer="orchestrator",
            payload={
                "task_id": task_id,
                "agent_id": "taizi",
                "state": "Taizi",
                "message": payload.get("title", ""),
            },
        )

    async def _on_state_changed(self, payload: dict):
        new_state = payload.get("to_state")
        task_id = payload.get("task_id")
        if not task_id or not new_state:
            return

        agent_id = self._get_next_agent(new_state)
        if agent_id:
            logger.info(f"Task {task_id}: state={new_state}, dispatching to {agent_id}")
            await self.bus.publish(
                TOPIC_TASK_DISPATCH,
                trace_id=payload.get("trace_id", ""),
                event_type="task.dispatch",
                producer="orchestrator",
                payload={
                    "task_id": task_id,
                    "agent_id": agent_id,
                    "state": new_state,
                    "message": "",
                },
            )

    def _get_next_agent(self, state: str) -> str | None:
        mapping = {
            "Taizi": "taizi",
            "Zhongshu": "zhongshu",
            "Menxia": "menxia",
            "Assigned": "shangshu",
            "Doing": None,
            "Review": "shangshu",
        }
        return mapping.get(state)

    async def _on_stalled(self, payload: dict):
        task_id = payload.get("task_id")
        stall_count = payload.get("stall_count", 0)
        state_str = payload.get("state", "")

        if stall_count <= MAX_STALL_RETRIES:
            logger.info(f"Task {task_id} stalled (count={stall_count}), retrying")
            await self.bus.publish(
                TOPIC_TASK_DISPATCH,
                trace_id=payload.get("trace_id", ""),
                event_type="task.dispatch",
                producer="orchestrator",
                payload={
                    "task_id": task_id,
                    "agent_id": self._get_next_agent(state_str) or "taizi",
                    "state": state_str,
                    "message": "重试：上次执行超时，请重新处理",
                },
            )
        else:
            try:
                state = TaskState(state_str)
                escalated = _ESCALATION_PATH.get(state)
                if escalated:
                    logger.info(f"Task {task_id} escalating: {state} -> {escalated}")
                    async with async_session() as db:
                        svc = TaskService(db)
                        await svc.transition_state(task_id, escalated, "orchestrator", "停滞升级")
            except Exception as e:
                logger.error(f"Escalation failed: {e}")

    async def _stall_detector_loop(self):
        while self._running:
            try:
                await self._detect_stalled_tasks()
            except Exception as e:
                logger.error(f"Stall detection error: {e}")
            await asyncio.sleep(60)

    async def _detect_stalled_tasks(self):
        threshold = datetime.utcnow() - timedelta(seconds=180)
        async with async_session() as db:
            result = await db.execute(
                select(Task).where(
                    Task.state.in_([TaskState.Doing, TaskState.Assigned]),
                    Task.updated_at < threshold,
                    Task.is_archived == False,
                )
            )
            stalled = result.scalars().all()
            for task in stalled:
                svc = TaskService(db)
                await svc.mark_stalled(str(task.id))


async def run_orchestrator():
    worker = OrchestratorWorker()
    await worker.start()
