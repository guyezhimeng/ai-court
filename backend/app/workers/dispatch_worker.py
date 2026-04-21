import asyncio
import json
import logging
import os
from datetime import datetime, timezone

import httpx

from app.config import settings
from app.services.event_bus import EventBus, get_event_bus, TOPIC_TASK_DISPATCH
from app.services.context_optimizer import context_optimizer
from app.services.task_service import TaskService
from app.services.llm_service import get_agent_llm_config
from app.db import async_session
from app.models.task import TaskState

logger = logging.getLogger(__name__)

GROUP = "dispatcher"
CONSUMER = f"disp-{os.getpid()}"

_BUCKET_CONFIG = {
    "fast": {"agents": {"taizi", "zhongshu", "menxia", "shangshu", "zaochao"}, "limit": 4},
    "slow": {"agents": {"hubu", "libu", "bingbu", "xingbu", "gongbu", "libu_hr"}, "limit": 3},
}

AGENT_TOOLS = {
    "hubu": [{
        "type": "function",
        "function": {
            "name": "submit_report",
            "description": "提交分析报告。当你的分析/计算/研究完成后，调用此函数提交结果。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "报告标题"},
                    "content": {"type": "string", "description": "报告正文，支持 Markdown"},
                    "key_findings": {"type": "array", "items": {"type": "string"}, "description": "关键发现列表"},
                },
                "required": ["title", "content"],
            },
        },
    }],
    "libu": [{
        "type": "function",
        "function": {
            "name": "submit_report",
            "description": "提交人事评估报告。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "recommendation": {"type": "string", "description": "建议"},
                },
                "required": ["title", "content"],
            },
        },
    }],
    "bingbu": [{
        "type": "function",
        "function": {
            "name": "submit_report",
            "description": "提交军事/安全分析报告。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "threat_level": {"type": "string", "enum": ["low", "medium", "high"]},
                },
                "required": ["title", "content"],
            },
        },
    }],
    "xingbu": [{
        "type": "function",
        "function": {
            "name": "submit_report",
            "description": "提交法律/合规审查报告。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "verdict": {"type": "string", "description": "审查结论"},
                },
                "required": ["title", "content"],
            },
        },
    }],
    "gongbu": [{
        "type": "function",
        "function": {
            "name": "submit_report",
            "description": "提交技术方案/工程报告。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "action_items": {"type": "array", "items": {"type": "string"}, "description": "行动项列表"},
                },
                "required": ["title", "content"],
            },
        },
    }],
    "libu_hr": [{
        "type": "function",
        "function": {
            "name": "submit_report",
            "description": "提交考核评估报告。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "score": {"type": "number", "description": "评分(0-100)"},
                },
                "required": ["title", "content"],
            },
        },
    }],
}


class DispatchWorker:
    def __init__(self):
        self.bus: EventBus | None = None
        self._running = False
        self._semaphores = {
            "fast": asyncio.Semaphore(_BUCKET_CONFIG["fast"]["limit"]),
            "slow": asyncio.Semaphore(_BUCKET_CONFIG["slow"]["limit"]),
        }
        self._http_client: httpx.AsyncClient | None = None

    @property
    def http_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=10, read=120, write=10, pool=10),
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            )
        return self._http_client

    async def start(self):
        self.bus = await get_event_bus()
        self._running = True
        logger.info("DispatchWorker started (direct LLM mode)")
        await self._consume_loop()

    async def stop(self):
        self._running = False
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
        logger.info("DispatchWorker stopped")

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
                    topic = event.get("topic", "")
                    msg_id = event.get("_msg_id", "")
                    await self.bus.ack(GROUP, topic, msg_id)

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

            full_result, tool_results = await self._call_llm_with_tools(
                agent_id=agent_id,
                message=enriched_message,
                system_prompt=system_prompt,
            )

            if not full_result and not tool_results:
                await self._mark_task_failed(task_id, agent_id, "LLM 调用失败，3 次重试均失败")
                return

            if tool_results:
                full_result = self._process_tool_results(agent_id, tool_results)

            await svc.update_task_summary(task_id, full_result, agent_id)

            if task.session_id:
                await self._write_agent_message_to_chat(task, agent_id, full_result)

            await self._append_context_chain(db, task, agent_id, full_result)

            await self.bus.publish(
                "agent.thoughts",
                trace_id=task.trace_id,
                event_type="agent.response",
                producer=agent_id,
                payload={
                    "task_id": task_id,
                    "agent_id": agent_id,
                    "response": full_result,
                    "has_tool_results": bool(tool_results),
                },
            )

            await self._advance_task_state(svc, task, agent_id, full_result)

    async def _call_llm_with_tools(
        self,
        agent_id: str,
        message: str,
        system_prompt: str = "",
    ) -> tuple[str, list[dict]]:
        llm_cfg = get_agent_llm_config(agent_id)
        tools = AGENT_TOOLS.get(agent_id, [])

        messages = [{"role": "system", "content": system_prompt}]
        messages.append({"role": "user", "content": message})

        request_body: dict = {
            "model": llm_cfg["model"],
            "messages": messages,
            "temperature": llm_cfg["temperature"],
        }
        if tools:
            request_body["tools"] = tools
        if llm_cfg["max_tokens"]:
            request_body["max_tokens"] = llm_cfg["max_tokens"]

        last_error = None
        for attempt in range(3):
            try:
                resp = await self.http_client.post(
                    f"{llm_cfg['api_url']}/chat/completions",
                    headers={"Authorization": f"Bearer {llm_cfg['api_key']}"},
                    json=request_body,
                )
                resp.raise_for_status()
                data = resp.json()

                choice = data["choices"][0]
                content = choice["message"].get("content", "") or ""
                tool_calls = choice["message"].get("tool_calls", [])

                if tool_calls:
                    messages.append(choice["message"])
                    for tc in tool_calls:
                        result = await self._handle_tool_call(agent_id, tc)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": json.dumps(result, ensure_ascii=False),
                        })

                    request_body_2: dict = {
                        "model": llm_cfg["model"],
                        "messages": messages,
                        "temperature": llm_cfg["temperature"],
                    }
                    if llm_cfg["max_tokens"]:
                        request_body_2["max_tokens"] = llm_cfg["max_tokens"]

                    resp2 = await self.http_client.post(
                        f"{llm_cfg['api_url']}/chat/completions",
                        headers={"Authorization": f"Bearer {llm_cfg['api_key']}"},
                        json=request_body_2,
                    )
                    resp2.raise_for_status()
                    data2 = resp2.json()
                    content = data2["choices"][0]["message"].get("content", "") or ""
                    return content, tool_calls

                return content.strip(), []

            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(f"LLM timeout for {agent_id}, attempt {attempt + 1}/3")
                await asyncio.sleep(2 ** attempt)
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    last_error = e
                    retry_after = int(e.response.headers.get("retry-after", "30"))
                    logger.warning(f"LLM rate limited for {agent_id}, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                else:
                    last_error = e
                    logger.error(f"LLM HTTP {e.response.status_code} for {agent_id}: {e}")
                    break
            except Exception as e:
                last_error = e
                logger.error(f"LLM call failed for {agent_id}: {e}")
                break

        logger.error(f"All retries exhausted for {agent_id}: {last_error}")
        return "", []

    async def _handle_tool_call(self, agent_id: str, tool_call: dict) -> dict:
        function_name = tool_call["function"]["name"]
        try:
            arguments = json.loads(tool_call["function"]["arguments"])
        except json.JSONDecodeError:
            return {"error": "Invalid JSON arguments"}

        if function_name == "submit_report":
            logger.info(f"[{agent_id}] submit_report: {arguments.get('title', 'untitled')}")
            return {
                "status": "ok",
                "message": f"报告 '{arguments.get('title', '')}' 已提交",
                "report_id": f"RPT-{hash(arguments.get('title', '')) % 10000:04d}",
            }
        else:
            return {"error": f"Unknown function: {function_name}"}

    def _process_tool_results(self, agent_id: str, tool_results: list[dict]) -> str:
        parts = []
        for tc in tool_results:
            func_name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"]["arguments"])
            except Exception:
                args = {}
            parts.append(f"**[{func_name}]** {args.get('title', '')} ✓")
        return "执行完成：\n" + "\n".join(parts)

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
            parts.append(f"当前进展: {task.now_summary[:500]}")
        return "\n".join(parts)

    async def _write_agent_message_to_chat(self, task, agent_id: str, result: str):
        async with async_session() as db:
            from app.services.chat_service import ChatService
            from app.services.event_bus import get_event_bus
            bus = await get_event_bus()
            svc = ChatService(db, bus)
            await svc.send_message(
                session_id=str(task.session_id),
                content=f"[{agent_id}] {result[:2000]}",
                role="agent",
                agent_id=agent_id,
                msg_type="task_update",
                metadata={"task_id": str(task.id)},
            )

    async def _append_context_chain(self, db, task, agent_id: str, result: str):
        if not task.context_chain:
            task.context_chain = []
        task.context_chain.append({
            "agent_id": agent_id,
            "response_summary": result[:1000],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        await db.commit()

    async def _advance_task_state(self, svc, task, agent_id: str, response: str):
        LIUBU = {"hubu", "libu", "bingbu", "xingbu", "gongbu", "libu_hr"}

        if agent_id in LIUBU and task.state == TaskState.Doing:
            await svc.transition_state(
                str(task.id), TaskState.Review, agent_id,
                f"六部执行完毕，提交审核\n{response[:200]}"
            )
        elif agent_id == "shangshu" and task.state == TaskState.Review:
            if "驳回" in response or "不通过" in response:
                await svc.transition_state(
                    str(task.id), TaskState.Menxia, agent_id,
                    f"尚书驳回，退回门下\n{response[:200]}"
                )
            else:
                await svc.transition_state(
                    str(task.id), TaskState.Done, agent_id,
                    f"尚书审核通过\n{response[:200]}"
                )

    async def _mark_task_failed(self, task_id: str, agent_id: str, reason: str):
        async with async_session() as db:
            svc = TaskService(db)
            try:
                await svc.transition_state(task_id, TaskState.Blocked, agent_id, reason)
            except Exception as e:
                logger.error(f"Failed to mark task {task_id} as blocked: {e}")


async def run_dispatcher():
    worker = DispatchWorker()
    await worker.start()
