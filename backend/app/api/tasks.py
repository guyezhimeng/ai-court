import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.task import Task, TaskState, TaskTransition
from app.services.task_service import TaskService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("")
async def list_tasks(
    state: str | None = None,
    is_archived: bool = False,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    svc = TaskService(db)
    task_state = TaskState(state) if state else None
    tasks = await svc.list_tasks(task_state, is_archived, limit, offset)
    return [_serialize_task(t) for t in tasks]


@router.get("/summary")
async def tasks_summary(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Task.state, func.count(Task.id))
        .where(Task.is_archived == False)
        .group_by(Task.state)
    )
    counts = {row[0].value: row[1] for row in result.all()}
    return {"counts": counts, "total": sum(counts.values())}


@router.get("/{task_id}")
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    svc = TaskService(db)
    task = await svc.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    data = _serialize_task(task)
    data["transitions"] = [
        {
            "from_state": t.from_state.value if t.from_state else None,
            "to_state": t.to_state.value,
            "agent_id": t.agent_id,
            "comment": t.comment,
            "created_at": t.created_at.isoformat(),
        }
        for t in task.transitions
    ]
    return data


@router.post("/{task_id}/transition")
async def transition_task(
    task_id: str,
    new_state: str = ...,
    agent_id: str | None = None,
    comment: str = "",
    db: AsyncSession = Depends(get_db),
):
    svc = TaskService(db)
    try:
        task = await svc.transition_state(
            task_id, TaskState(new_state), agent_id, comment
        )
        return _serialize_task(task)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{task_id}/archive")
async def archive_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    svc = TaskService(db)
    task = await svc.archive_task(task_id)
    return _serialize_task(task)


@router.post("/{task_id}/dispatch")
async def dispatch_task(
    task_id: str,
    agent_id: str = ...,
    message: str = "",
    db: AsyncSession = Depends(get_db),
):
    svc = TaskService(db)
    await svc.request_dispatch(task_id, agent_id, message)
    return {"status": "dispatch_requested"}


def _serialize_task(task: Task) -> dict:
    return {
        "id": str(task.id),
        "trace_id": task.trace_id,
        "title": task.title,
        "description": task.description,
        "state": task.state.value,
        "priority": task.priority,
        "department": task.department,
        "assignee": task.assignee,
        "subtasks": task.subtasks,
        "now_summary": task.now_summary,
        "blockers": task.blockers,
        "todos": task.todos,
        "stall_count": task.stall_count,
        "review_round": task.review_round,
        "is_archived": task.is_archived,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }
