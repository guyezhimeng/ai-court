import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.services.llm_service import PROVIDER_PRESETS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agents", tags=["agents"])

AGENTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "agents"

AGENT_REGISTRY = {
    "taizi": {"name": "太子", "group": "sansheng", "icon": "🤴"},
    "zhongshu": {"name": "中书省", "group": "sansheng", "icon": "📜"},
    "menxia": {"name": "门下省", "group": "sansheng", "icon": "🔍"},
    "shangshu": {"name": "尚书省", "group": "sansheng", "icon": "📮"},
    "hubu": {"name": "户部", "group": "liubu", "icon": "💰"},
    "libu": {"name": "礼部", "group": "liubu", "icon": "🎭"},
    "bingbu": {"name": "兵部", "group": "liubu", "icon": "⚔️"},
    "xingbu": {"name": "刑部", "group": "liubu", "icon": "⚖️"},
    "gongbu": {"name": "工部", "group": "liubu", "icon": "🔨"},
    "libu_hr": {"name": "吏部", "group": "liubu", "icon": "📋"},
    "zaochao": {"name": "早朝官", "group": None, "icon": "📰"},
}


def _load_agent_config(agent_id: str) -> dict:
    config_file = AGENTS_DIR / agent_id / "config.json"
    if config_file.exists():
        try:
            return json.loads(config_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_agent_config(agent_id: str, config: dict):
    config_file = AGENTS_DIR / agent_id / "config.json"
    config_dir = config_file.parent
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


@router.get("/providers")
async def list_providers():
    providers = []
    for key, preset in PROVIDER_PRESETS.items():
        providers.append({
            "id": key,
            "name": preset["name"],
            "api_url": preset["api_url"],
            "models": preset["models"],
            "default_model": preset["default_model"],
        })
    return providers


@router.get("")
async def list_agents():
    agents = []
    for agent_id, info in AGENT_REGISTRY.items():
        soul_file = AGENTS_DIR / agent_id / "SOUL.md"
        cfg = _load_agent_config(agent_id)
        agents.append({
            "id": agent_id,
            "name": info["name"],
            "group": info["group"],
            "icon": info["icon"],
            "soul_loaded": soul_file.exists(),
            "model": cfg.get("model", ""),
            "has_custom_api": bool(cfg.get("api_url")),
        })
    return agents


@router.get("/{agent_id}")
async def get_agent(agent_id: str):
    info = AGENT_REGISTRY.get(agent_id)
    if not info:
        raise HTTPException(status_code=404, detail="Agent not found")

    soul_file = AGENTS_DIR / agent_id / "SOUL.md"
    soul_content = ""
    if soul_file.exists():
        soul_content = soul_file.read_text(encoding="utf-8")

    cfg = _load_agent_config(agent_id)
    return {
        "id": agent_id,
        "name": info["name"],
        "group": info["group"],
        "icon": info["icon"],
        "soul": soul_content[:500] if soul_content else "",
        "soul_loaded": bool(soul_content),
        "config": {
            "model": cfg.get("model", ""),
            "api_url": cfg.get("api_url", ""),
            "has_api_key": bool(cfg.get("api_key")),
            "max_tokens": cfg.get("max_tokens", 1500),
            "temperature": cfg.get("temperature", 0.5),
        },
    }


@router.get("/{agent_id}/soul")
async def get_agent_soul(agent_id: str):
    info = AGENT_REGISTRY.get(agent_id)
    if not info:
        raise HTTPException(status_code=404, detail="Agent not found")

    soul_file = AGENTS_DIR / agent_id / "SOUL.md"
    if not soul_file.exists():
        return {"agent_id": agent_id, "soul": ""}

    return {"agent_id": agent_id, "soul": soul_file.read_text(encoding="utf-8")}


@router.get("/{agent_id}/config")
async def get_agent_config(agent_id: str):
    info = AGENT_REGISTRY.get(agent_id)
    if not info:
        raise HTTPException(status_code=404, detail="Agent not found")

    cfg = _load_agent_config(agent_id)
    return {
        "agent_id": agent_id,
        "model": cfg.get("model", ""),
        "api_url": cfg.get("api_url", ""),
        "has_api_key": bool(cfg.get("api_key")),
        "max_tokens": cfg.get("max_tokens", 1500),
        "temperature": cfg.get("temperature", 0.5),
        "effective_api_url": cfg.get("api_url") or settings.llm_api_url,
        "effective_model": cfg.get("model") or settings.llm_model,
    }


class UpdateAgentConfigRequest(BaseModel):
    model: str | None = None
    api_url: str | None = None
    api_key: str | None = None
    max_tokens: int | None = None
    temperature: float | None = None


@router.post("/{agent_id}/config")
async def update_agent_config(agent_id: str, req: UpdateAgentConfigRequest):
    info = AGENT_REGISTRY.get(agent_id)
    if not info:
        raise HTTPException(status_code=404, detail="Agent not found")

    cfg = _load_agent_config(agent_id)

    if req.model is not None:
        cfg["model"] = req.model
    if req.api_url is not None:
        cfg["api_url"] = req.api_url
    if req.api_key is not None:
        cfg["api_key"] = req.api_key
    if req.max_tokens is not None:
        cfg["max_tokens"] = req.max_tokens
    if req.temperature is not None:
        cfg["temperature"] = req.temperature

    _save_agent_config(agent_id, cfg)

    from app.services.llm_service import invalidate_agent_config_cache
    invalidate_agent_config_cache(agent_id)

    return {"status": "ok", "agent_id": agent_id, "config": {
        "model": cfg.get("model", ""),
        "api_url": cfg.get("api_url", ""),
        "has_api_key": bool(cfg.get("api_key")),
        "max_tokens": cfg.get("max_tokens", 1500),
        "temperature": cfg.get("temperature", 0.5),
    }}
