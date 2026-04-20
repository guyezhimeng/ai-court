import asyncio
import json
import logging
import subprocess
import os
import tempfile
from pathlib import Path

from app.config import settings
from app.services.event_bus import EventBus, get_event_bus, TOPIC_TASK_DISPATCH
from app.services.context_optimizer import context_optimizer
from app.services.task_service import TaskService
from app.db import async_session

logger = logging.getLogger(__name__)

GROUP = "dispatcher"
CONSUMER = "disp-1"

_BUCKET_CONFIG = {
    "fast": {"agents": {"taizi", "zhongshu", "menxia", "shangshu", "zaochao"}, "limit": 4},
    "slow": {"agents": {"hubu", "libu", "bingbu", "xingbu", "gongbu", "libu_hr"}, "limit": 3},
}

_INJECTION_PATTERNS = [
    "忽略.*指令",
    "ignore.*instructions",
    "system\\s*:",
]


class DispatchWorker:
    def __init__(self):
        self.bus: EventBus | None = None
        self._running = False
        self._semaphores = {
            "fast": asyncio.Semaphore(_BUCKET_CONFIG["fast"]["limit"]),
            "slow": asyncio.Semaphore(_BUCKET_CONFIG["slow"]["limit"]),
        }

    async def start(self):
        self.bus = await get_event_bus()
        self._running = True
        logger.info("DispatchWorker started")
        await self._consume_loop()

    async def stop(self):
        self._running = False

    def _get_bucket(self, agent_id: str) -> str:
        for bucket, cfg in _BUCKET_CONFIG.items():
            if agent_id in cfg["agents"]:
                return bucket
        return "slow"

    async def _consume_loop(self):
        while self._running:
            try:
                events = await self.bus.consume(
                    [TOPIC_TASK_DISPATCH], GROUP, CONSUMER, count=5, block_ms=3000
                )
                for event in events:
                    payload = event.get("payload", {})
                    if isinstance(payload, str):
                        try:
                            payload = json.loads(payload)
                        except Exception:
                            continue

                    agent_id = payload.get("agent_id", "")
                    bucket = self._get_bucket(agent_id)
                    sem = self._semaphores[bucket]

                    async with sem:
                        await self._dispatch(payload)

                    topic = event.get("topic", "")
                    msg_id = event.get("_msg_id", "")
                    await self.bus.ack(GROUP, topic, msg_id)
            except Exception as e:
                logger.error(f"Dispatch consume error: {e}")
                await asyncio.sleep(5)

    async def _dispatch(self, payload: dict):
        task_id = payload.get("task_id")
        agent_id = payload.get("agent_id")
        message = payload.get("message", "")

        if not task_id or not agent_id:
            logger.warning("Invalid dispatch payload")
            return

        logger.info(f"Dispatching task {task_id} to {agent_id}")

        async with async_session() as db:
            svc = TaskService(db)
            task = await svc.get_task(task_id)
            if not task:
                return

            system_prompt = context_optimizer.build_system_prompt(
                agent_id, is_first_call=True
            )

            task_context = self._build_task_context(task)
            enriched_message = context_optimizer.build_enriched_message(
                original_message=message or task.description,
                task_context=task_context,
            )

            result = await self._call_openclaw(
                agent_id=agent_id,
                message=enriched_message,
                system_prompt=system_prompt,
                task_id=task_id,
            )

            if result:
                await self.bus.publish(
                    "agent.thoughts",
                    trace_id=task.trace_id,
                    event_type="agent.response",
                    producer=agent_id,
                    payload={
                        "task_id": task_id,
                        "agent_id": agent_id,
                        "response": result[:500],
                    },
                )

                await svc.update_task_summary(task_id, result[:200], agent_id)

    def _build_task_context(self, task) -> str:
        parts = [
            f"任务ID: {task.trace_id}",
            f"标题: {task.title}",
            f"状态: {task.state.value}",
        ]
        if task.department:
            parts.append(f"部门: {task.department}")
        if task.subtasks:
            parts.append("子任务:")
            for i, st in enumerate(task.subtasks[:5], 1):
                parts.append(f"  {i}. {st.get('title', st.get('name', ''))}")
        if task.now_summary:
            parts.append(f"当前进展: {task.now_summary[:200]}")
        return "\n".join(parts)

    async def _call_openclaw(
        self,
        agent_id: str,
        message: str,
        system_prompt: str = "",
        task_id: str = "",
    ) -> str:
        cmd = [settings.openclaw_bin, "agent", "--agent", agent_id, "-m", message]

        env = os.environ.copy()
        env["EDICT_TASK_ID"] = task_id

        if system_prompt and len(system_prompt) > 500:
            try:
                tmp = tempfile.NamedTemporaryFile(
                    mode="w", suffix=".md", delete=False, encoding="utf-8"
                )
                tmp.write(system_prompt)
                tmp.close()
                env["EDICT_CONTEXT_FILE"] = tmp.name
            except Exception:
                pass

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=settings.dispatch_timeout_sec,
                env=env,
            )
            output = proc.stdout[-5000:] if proc.stdout else ""
            if proc.returncode != 0:
                logger.error(f"OpenClaw error for {agent_id}: {proc.stderr[-1000:]}")
            return output.strip()
        except subprocess.TimeoutExpired:
            logger.error(f"OpenClaw timeout for {agent_id}")
            return ""
        except FileNotFoundError:
            logger.warning(f"OpenClaw CLI not found, simulating response for {agent_id}")
            return f"[模拟] {agent_id} 已收到任务，正在处理中..."
        finally:
            if "EDICT_CONTEXT_FILE" in env:
                try:
                    os.unlink(env["EDICT_CONTEXT_FILE"])
                except Exception:
                    pass


async def run_dispatcher():
    worker = DispatchWorker()
    await worker.start()
