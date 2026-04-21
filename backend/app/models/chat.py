import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Text, Boolean, DateTime, ForeignKey, Index,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db import Base


def _utcnow():
    return datetime.now(timezone.utc)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(100), default="default_user", index=True)
    title = Column(String(255), default="")
    type = Column(String(20), default="chat")
    task_id = Column(String(50), nullable=True)
    regime = Column(String(20), default="tang-sansheng")
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    messages = relationship(
        "ChatMessage", back_populates="session",
        order_by="ChatMessage.created_at", lazy="selectin",
    )
    tasks = relationship("Task", backref="chat_session", lazy="selectin")

    __table_args__ = (
        Index("ix_sessions_user_updated", "user_id", "updated_at"),
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    agent_id = Column(String(50), nullable=True)
    content = Column(Text, default="")
    msg_type = Column(String(20), default="text")
    metadata_ = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime, default=_utcnow)

    session = relationship("ChatSession", back_populates="messages")
    attachments = relationship("Attachment", back_populates="message", lazy="selectin")

    __table_args__ = (
        Index("ix_messages_session_created", "session_id", "created_at"),
        Index(
            "ix_messages_content_fts",
            text("to_tsvector('simple', content)"),
            postgresql_using="gin",
        ),
    )
