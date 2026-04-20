import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, Integer, Boolean, BigInteger, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db import Base


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    topic = Column(String(100), nullable=False, index=True)
    trace_id = Column(String(64), nullable=False, index=True)
    event_type = Column(String(100), nullable=False)
    payload = Column(JSONB, default=dict)
    published = Column(Boolean, default=False, index=True)
    attempts = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)
