import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.services.chat_service import ChatService
from app.services.event_bus import get_event_bus, EventBus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


class CreateSessionRequest(BaseModel):
    user_id: str = "default_user"
    regime: str = "tang-sansheng"


class SendMessageRequest(BaseModel):
    session_id: str
    content: str
    attachments: list[str] | None = None


class SearchRequest(BaseModel):
    query: str
    limit: int = 20


@router.post("/sessions")
async def create_session(
    req: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
    bus: EventBus = Depends(get_event_bus),
):
    svc = ChatService(db, bus)
    session = await svc.create_session(user_id=req.user_id, regime=req.regime)
    return {
        "id": str(session.id),
        "user_id": session.user_id,
        "title": session.title,
        "type": session.type,
        "regime": session.regime,
        "created_at": session.created_at.isoformat(),
    }


@router.get("/sessions")
async def list_sessions(
    user_id: str = "default_user",
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    bus: EventBus = Depends(get_event_bus),
):
    svc = ChatService(db, bus)
    sessions = await svc.list_sessions(user_id, limit, offset)
    return [
        {
            "id": str(s.id),
            "title": s.title,
            "type": s.type,
            "regime": s.regime,
            "updated_at": s.updated_at.isoformat(),
            "is_archived": s.is_archived,
        }
        for s in sessions
    ]


@router.post("/send")
async def send_message(
    req: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    bus: EventBus = Depends(get_event_bus),
):
    svc = ChatService(db, bus)
    attachments = None
    if req.attachments:
        attachments = [{"id": aid} for aid in req.attachments]

    result = await svc.handle_user_message(
        session_id=req.session_id,
        content=req.content,
        attachments=attachments,
    )
    return result


@router.get("/history/{session_id}")
async def get_history(
    session_id: str,
    limit: int = 50,
    before: str | None = None,
    db: AsyncSession = Depends(get_db),
    bus: EventBus = Depends(get_event_bus),
):
    svc = ChatService(db, bus)
    messages = await svc.get_history(session_id, limit, before)
    return [
        {
            "id": str(m.id),
            "role": m.role,
            "agent_id": m.agent_id,
            "content": m.content,
            "msg_type": m.msg_type,
            "metadata": m.metadata_,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]


@router.post("/search")
async def search_messages(
    req: SearchRequest,
    user_id: str = "default_user",
    db: AsyncSession = Depends(get_db),
    bus: EventBus = Depends(get_event_bus),
):
    svc = ChatService(db, bus)
    messages = await svc.search_messages(user_id, req.query, req.limit)
    return [
        {
            "id": str(m.id),
            "session_id": str(m.session_id),
            "role": m.role,
            "content": m.content[:200],
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]
