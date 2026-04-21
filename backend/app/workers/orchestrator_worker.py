import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone

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
from app.services.review_strategy import review_strategy

logger = logging.getLogger(__name__)

GROUP = "orchestrator"
CONSUMER = os.getenv("WORKER_ID", f"orch-{os.getpid()}")
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
        logger.info("OrchestratorWorker stopping...")
        self._running = False
        await asyncio.sleep(1)
        logger.info("OrchestratorWorker stopped")

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

        if new_state == "Menxia":
            await self._handle_menxia_review(task_id, payload)
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

    async def _handle_menxia_review(self, task_id: str, payload: dict):
        async with async_session() as db:
            svc = TaskService(db)
            task = await svc.get_task(task_id)
            if not task:
                return

            review_level = review_strategy.decide_review_level(task)
            review_result = await review_strategy.execute_review(task, review_level)

            result_text = review_result.get("result", "")

            if "驳回" in result_text:
                await svc.transition_state(
                    task_id, TaskState.Zhongshu, "menxia",
                    f"门下驳回：{review_result.get('reason', '')}\n{result_text[:200]}"
                )
            else:
                await svc.transition_state(
                    task_id, TaskState.Assigned, "menxia",
                    f"门下审核通过（{review_level}）：{review_result.get('reason', '')}"
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
        from app.config import settings
        threshold = datetime.now(timezone.utc) - timedelta(seconds=settings.stall_threshold_sec)
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

    async def _dispatch_to_liubu(self, task: Task, departments: list[str]):
        dispatch_tasks = []
        for dept in departments:
            from app.models.task import ORG_AGENT_MAP
            agent_id = ORG_AGENT_MAP.get(dept, dept)
            dispatch_tasks.append(
                self.bus.publish(
                    TOPIC_TASK_DISPATCH,
                    trace_id=task.trace_id,
                    event_type="task.dispatch",
                    producer="shangshu",
                    payload={
                        "task_id": str(task.id),
                        "agent_id": agent_id,
                        "message": f"尚书省指派任务，请{dept}执行。",
                    },
                )
            )

        await asyncio.gather(*dispatch_tasks)
        logger.info(f"Task {task.trace_id}: parallel dispatched to {departments}")


async def run_orchestrator():
    worker = OrchestratorWorker()
    await worker.start()
