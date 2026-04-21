import logging
import os
import traceback
import uuid
from contextlib import asynccontextmanager
from contextvars import ContextVar

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db import engine, Base
from app.services.event_bus import get_event_bus
from app.api import chat, upload, websocket, tasks, agents

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


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
    description="三省六部 AI 多 Agent 协作系统",
    version="3.0.0",
    lifespan=lifespan,
)

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.middleware("http")
async def trace_id_middleware(request: Request, call_next):
    tid = request.headers.get("X-Trace-ID", str(uuid.uuid4())[:8])
    trace_id_var.set(tid)
    response = await call_next(request)
    response.headers["X-Trace-ID"] = tid
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_id = str(uuid.uuid4())[:8]
    logger.error(
        f"[{trace_id_var.get()}] Unhandled {request.method} {request.url}: "
        f"{exc}\n{traceback.format_exc()}"
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "服务器内部错误，请稍后重试",
            "error_id": error_id,
        },
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
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
    checks = {"status": "ok", "version": "3.0.0", "services": {}}

    try:
        from app.db import async_session
        from sqlalchemy import text
        async with async_session() as db:
            await db.execute(text("SELECT 1"))
        checks["services"]["postgres"] = "ok"
    except Exception as e:
        checks["services"]["postgres"] = f"error: {e}"
        checks["status"] = "degraded"

    try:
        bus = await get_event_bus()
        await bus.redis.ping()
        checks["services"]["redis"] = "ok"
    except Exception as e:
        checks["services"]["redis"] = f"error: {e}"
        checks["status"] = "degraded"

    try:
        from app.services.llm_service import AGENTS_DIR
        if AGENTS_DIR.exists():
            agent_count = len([d for d in AGENTS_DIR.iterdir() if d.is_dir()])
            checks["services"]["agents"] = f"ok ({agent_count} agents)"
        else:
            checks["services"]["agents"] = "error: AGENTS_DIR not found"
            checks["status"] = "degraded"
    except Exception as e:
        checks["services"]["agents"] = f"error: {e}"
        checks["status"] = "degraded"

    status_code = 200 if checks["status"] == "ok" else 503
    return JSONResponse(content=checks, status_code=status_code)


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
