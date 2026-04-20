import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db import engine, Base
from app.services.event_bus import get_event_bus
from app.api import chat, upload, websocket, tasks, agents

import os

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    bus = await get_event_bus()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("AI Court backend started")
    yield
    await bus.close()
    await engine.dispose()
    logger.info("AI Court backend stopped")


app = FastAPI(
    title="AI 朝廷",
    description="三省六部 AI 多 Agent 协作系统 - 内置聊天框 + 看板",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(upload.router)
app.include_router(tasks.router)
app.include_router(agents.router)
app.include_router(websocket.router)


upload_dir = os.path.abspath(settings.upload_dir)
os.makedirs(upload_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "2.0.0"}


@app.get("/api/live-status")
async def live_status():
    from app.db import async_session
    from app.models.task import Task, TaskState
    from sqlalchemy import select, func

    async with async_session() as db:
        result = await db.execute(
            select(Task.state, func.count(Task.id))
            .where(Task.is_archived == False)
            .group_by(Task.state)
        )
        counts = {row[0].value: row[1] for row in result.all()}
        return {"tasks": counts, "total": sum(counts.values())}
