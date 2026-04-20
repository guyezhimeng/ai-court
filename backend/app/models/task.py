import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Text, Enum, Integer, BigInteger,
    Boolean, JSON, DateTime, ForeignKey, Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db import Base


class TaskState(str, enum.Enum):
    Taizi = "Taizi"
    Zhongshu = "Zhongshu"
    Menxia = "Menxia"
    Assigned = "Assigned"
    Doing = "Doing"
    Review = "Review"
    Done = "Done"
    Blocked = "Blocked"
    Cancelled = "Cancelled"


STATE_TRANSITIONS = {
    TaskState.Taizi: {TaskState.Zhongshu, TaskState.Cancelled},
    TaskState.Zhongshu: {TaskState.Menxia, TaskState.Cancelled, TaskState.Blocked},
    TaskState.Menxia: {TaskState.Assigned, TaskState.Zhongshu, TaskState.Cancelled},
    TaskState.Assigned: {TaskState.Doing, TaskState.Cancelled, TaskState.Blocked},
    TaskState.Doing: {TaskState.Review, TaskState.Done, TaskState.Blocked, TaskState.Cancelled},
    TaskState.Review: {TaskState.Done, TaskState.Menxia, TaskState.Doing, TaskState.Cancelled},
    TaskState.Blocked: {TaskState.Taizi, TaskState.Zhongshu, TaskState.Menxia, TaskState.Assigned, TaskState.Doing},
    TaskState.Done: set(),
    TaskState.Cancelled: set(),
}

STATE_AGENT_MAP = {
    TaskState.Taizi: "taizi",
    TaskState.Zhongshu: "zhongshu",
    TaskState.Menxia: "menxia",
    TaskState.Assigned: "shangshu",
    TaskState.Review: "shangshu",
}

ORG_AGENT_MAP = {
    "户部": "hubu",
    "礼部": "libu",
    "兵部": "bingbu",
    "刑部": "xingbu",
    "工部": "gongbu",
    "吏部": "libu_hr",
}


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trace_id = Column(String(64), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, default="")
    state = Column(Enum(TaskState), default=TaskState.Taizi, nullable=False, index=True)
    priority = Column(String(20), default="normal")
    department = Column(String(50))
    assignee = Column(String(50))
    subtasks = Column(JSONB, default=list)
    now_summary = Column(Text, default="")
    blockers = Column(JSONB, default=list)
    todos = Column(JSONB, default=list)
    stall_count = Column(Integer, default=0)
    review_round = Column(Integer, default=0)
    context_chain = Column(JSONB, default=list)
    metadata_ = Column("metadata", JSONB, default=dict)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    is_archived = Column(Boolean, default=False)

    attachments = relationship("Attachment", back_populates="task", lazy="selectin")
    transitions = relationship("TaskTransition", back_populates="task", lazy="selectin",
                               order_by="TaskTransition.created_at")

    __table_args__ = (
        Index("ix_tasks_state_archived", "state", "is_archived"),
    )


class TaskTransition(Base):
    __tablename__ = "task_transitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False, index=True)
    from_state = Column(Enum(TaskState), nullable=True)
    to_state = Column(Enum(TaskState), nullable=False)
    agent_id = Column(String(50))
    comment = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="transitions")
