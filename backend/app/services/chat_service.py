import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatSession, ChatMessage
from app.models.task import Task, TaskState
from app.models.outbox import OutboxEvent
from app.services.event_bus import (
    EventBus, TOPIC_TASK_CREATED, TOPIC_CHAT_MESSAGE,
)

logger = logging.getLogger(__name__)

_STRONG_DECREE_KEYWORDS = [
    "下旨", "旨意", "圣旨", "命令你", "执行任务",
    "开发一个", "编写一个", "创建一个", "部署",
    "修复", "优化", "实现", "完成",
    "帮我做", "帮我写", "帮我建", "帮我分析",
]

_WEAK_DECREE_KEYWORDS = [
    "任务", "分析", "审查", "设计", "报告",
]

_CHAT_KEYWORDS = [
    "你好", "嗨", "在吗", "怎么样", "谢谢", "再见",
    "你是谁", "什么意思", "为什么",
]


class ChatService:
    def __init__(self, db: AsyncSession, event_bus: EventBus):
        self.db = db
        self.bus = event_bus

    async def create_session(
        self, user_id: str = "default_user", regime: str = "tang-sansheng"
    ) -> ChatSession:
        session = ChatSession(
            user_id=user_id,
            type="chat",
            regime=regime,
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        result = await self.db.execute(
            select(ChatSession).where(ChatSession.id == uuid.UUID(session_id))
        )
        return result.scalar_one_or_none()

    async def list_sessions(
        self, user_id: str, limit: int = 20, offset: int = 0
    ) -> list[ChatSession]:
        result = await self.db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id, ChatSession.is_archived == False)
            .order_by(ChatSession.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def send_message(
        self,
        session_id: str,
        content: str,
        role: str = "user",
        agent_id: str | None = None,
        msg_type: str = "text",
        metadata: dict | None = None,
    ) -> ChatMessage:
        msg = ChatMessage(
            session_id=uuid.UUID(session_id),
            role=role,
            agent_id=agent_id,
            content=content,
            msg_type=msg_type,
            metadata_=metadata or {},
        )
        self.db.add(msg)

        session = await self.get_session(session_id)
        if session:
            session.updated_at = datetime.now(timezone.utc)
            if not session.title and role == "user":
                session.title = content[:50]

        await self.db.commit()
        await self.db.refresh(msg)

        await self.bus.publish(
            topic=TOPIC_CHAT_MESSAGE,
            trace_id=session_id,
            event_type="message.created",
            producer=role,
            payload={
                "message_id": str(msg.id),
                "session_id": session_id,
                "role": role,
                "agent_id": agent_id,
                "content": content[:200],
                "msg_type": msg_type,
            },
        )

        return msg

    def classify_message(self, content: str) -> str:
        content_stripped = content.strip()

        if len(content_stripped) < 3:
            return "chat"

        strong_count = sum(1 for kw in _STRONG_DECREE_KEYWORDS if kw in content_stripped)
        if strong_count > 0:
            return "decree"

        structural_hints = 0
        if len(content_stripped) > 50:
            structural_hints += 1
        if "\n" in content_stripped:
            structural_hints += 1
        if re.search(r'[1-9][.)、]', content_stripped):
            structural_hints += 1
        if any(p in content_stripped for p in ["：", ":", "步骤", "要求"]):
            structural_hints += 1
        if structural_hints >= 2:
            return "decree"

        weak_count = sum(1 for kw in _WEAK_DECREE_KEYWORDS if kw in content_stripped)
        chat_count = sum(1 for kw in _CHAT_KEYWORDS if kw in content_stripped)

        if weak_count > 0 and chat_count == 0:
            return "decree"

        return "chat"

    async def handle_user_message(
        self,
        session_id: str,
        content: str,
        attachments: list[dict] | None = None,
    ) -> dict:
        user_msg = await self.send_message(
            session_id=session_id,
            content=content,
            role="user",
            msg_type="text",
            metadata={"attachments": [a["id"] for a in (attachments or [])]},
        )

        msg_type = self.classify_message(content)

        if msg_type == "decree":
            session = await self.get_session(session_id)
            if session:
                session.type = "decree"

            task = await self._create_task_from_decree(session_id, content, attachments)
            return {
                "type": "decree",
                "message_id": str(user_msg.id),
                "task_id": str(task.id),
                "trace_id": task.trace_id,
                "state": task.state.value,
                "info": "旨意已下达，太子正在分拣...",
            }
        else:
            reply = await self._handle_idle_chat(session_id, content)
            return {
                "type": "chat",
                "message_id": str(user_msg.id),
                "reply_message_id": str(reply.id),
                "content": reply.content,
            }

    async def handle_user_message_stream(
        self,
        session_id: str,
        content: str,
        attachments: list[dict] | None = None,
    ):
        from app.services.llm_service import stream_llm_reply

        user_msg = await self.send_message(
            session_id=session_id,
            content=content,
            role="user",
            msg_type="text",
            metadata={"attachments": [a["id"] for a in (attachments or [])]},
        )

        msg_type = self.classify_message(content)

        if msg_type == "decree":
            session = await self.get_session(session_id)
            if session:
                session.type = "decree"

            task = await self._create_task_from_decree(session_id, content, attachments)
            yield f"data: {json.dumps({'type': 'decree', 'task_id': str(task.id), 'trace_id': task.trace_id, 'info': '旨意已下达，太子正在分拣...'}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        else:
            history = await self._get_recent_messages(session_id, limit=10)
            full_content = ""

            yield f"data: {json.dumps({'type': 'chat_start', 'message_id': str(user_msg.id)}, ensure_ascii=False)}\n\n"

            async for chunk in stream_llm_reply(content, history, agent_id="taizi"):
                full_content += chunk
                yield f"data: {json.dumps({'type': 'chat_chunk', 'content': chunk}, ensure_ascii=False)}\n\n"

            reply = await self.send_message(
                session_id=session_id,
                content=full_content,
                role="agent",
                agent_id="taizi",
                msg_type="text",
            )

            yield f"data: {json.dumps({'type': 'chat_end', 'reply_message_id': str(reply.id)}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    async def _create_task_from_decree(
        self,
        session_id: str,
        content: str,
        attachments: list[dict] | None = None,
    ) -> Task:
        trace_id = f"JJC-{uuid.uuid4().hex[:8].upper()}"
        task = Task(
            trace_id=trace_id,
            title=content[:100],
            description=content,
            state=TaskState.Taizi,
            session_id=uuid.UUID(session_id),
            metadata_={"attachments": [a["id"] for a in (attachments or [])]},
        )
        self.db.add(task)

        outbox = OutboxEvent(
            topic=TOPIC_TASK_CREATED,
            trace_id=trace_id,
            event_type="task.created",
            payload={
                "task_id": str(task.id),
                "trace_id": trace_id,
                "title": content[:100],
                "session_id": session_id,
            },
        )
        self.db.add(outbox)

        await self.db.commit()
        await self.db.refresh(task)

        await self.send_message(
            session_id=session_id,
            content=f"旨意已录入【{trace_id}】，太子正在分拣...",
            role="system",
            msg_type="task_update",
            metadata={"task_id": str(task.id), "state": "Taizi"},
        )

        return task

    async def _handle_idle_chat(self, session_id: str, content: str) -> ChatMessage:
        from app.services.llm_service import get_llm_reply

        history = await self._get_recent_messages(session_id, limit=10)
        reply_text = await get_llm_reply(content, history, agent_id="taizi")

        reply = await self.send_message(
            session_id=session_id,
            content=reply_text,
            role="agent",
            agent_id="taizi",
            msg_type="text",
        )
        return reply

    async def _get_recent_messages(
        self, session_id: str, limit: int = 10
    ) -> list[dict]:
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == uuid.UUID(session_id))
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        messages = list(result.scalars().all())
        messages.reverse()
        return [
            {"role": m.role, "content": m.content, "agent_id": m.agent_id}
            for m in messages
        ]

    async def get_history(
        self, session_id: str, limit: int = 50, before: str | None = None
    ) -> list[ChatMessage]:
        query = (
            select(ChatMessage)
            .where(ChatMessage.session_id == uuid.UUID(session_id))
            .order_by(ChatMessage.created_at.desc())
        )
        if before:
            query = query.where(
                ChatMessage.created_at
                < select(ChatMessage.created_at).where(
                    ChatMessage.id == uuid.UUID(before)
                )
            )
        query = query.limit(limit)
        result = await self.db.execute(query)
        messages = list(result.scalars().all())
        messages.reverse()
        return messages

    async def search_messages(
        self, user_id: str, query: str, limit: int = 20
    ) -> list[ChatMessage]:
        tsquery = func.plainto_tsquery('simple', query)
        result = await self.db.execute(
            select(ChatMessage)
            .join(ChatSession)
            .where(
                ChatSession.user_id == user_id,
                func.to_tsvector('simple', ChatMessage.content).op('@@')(tsquery),
            )
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
