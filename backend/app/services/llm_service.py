import json
import logging
from pathlib import Path
from typing import AsyncGenerator, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

AGENTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "agents"

_agent_configs: dict[str, dict] = {}

PROVIDER_PRESETS = {
    "deepseek": {
        "name": "DeepSeek",
        "api_url": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "default_model": "deepseek-chat",
    },
    "openai": {
        "name": "OpenAI",
        "api_url": "https://api.openai.com/v1",
        "models": ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1"],
        "default_model": "gpt-4o-mini",
    },
    "moonshot": {
        "name": "月之暗面(Kimi)",
        "api_url": "https://api.moonshot.cn/v1",
        "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
        "default_model": "moonshot-v1-8k",
    },
    "qwen": {
        "name": "通义千问",
        "api_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": ["qwen-plus", "qwen-turbo", "qwen-max"],
        "default_model": "qwen-plus",
    },
    "zhipu": {
        "name": "智谱(GLM)",
        "api_url": "https://open.bigmodel.cn/api/paas/v4",
        "models": ["glm-4-flash", "glm-4-plus", "glm-4"],
        "default_model": "glm-4-flash",
    },
    "siliconflow": {
        "name": "硅基流动",
        "api_url": "https://api.siliconflow.cn/v1",
        "models": ["Qwen/Qwen2.5-7B-Instruct", "deepseek-ai/DeepSeek-V3"],
        "default_model": "Qwen/Qwen2.5-7B-Instruct",
    },
    "custom": {
        "name": "自定义",
        "api_url": "",
        "models": [],
        "default_model": "",
    },
}


def load_agent_config(agent_id: str) -> dict:
    if agent_id in _agent_configs:
        return _agent_configs[agent_id]

    config_file = AGENTS_DIR / agent_id / "config.json"
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            _agent_configs[agent_id] = cfg
            return cfg
        except Exception as e:
            logger.warning(f"Failed to load config for {agent_id}: {e}")

    return {}


def get_agent_llm_config(agent_id: str) -> dict:
    agent_cfg = load_agent_config(agent_id)
    return {
        "api_url": agent_cfg.get("api_url") or settings.llm_api_url,
        "api_key": agent_cfg.get("api_key") or settings.llm_api_key,
        "model": agent_cfg.get("model") or settings.llm_model,
        "max_tokens": agent_cfg.get("max_tokens", 1500),
        "temperature": agent_cfg.get("temperature", 0.5),
    }


def invalidate_agent_config_cache(agent_id: str | None = None):
    if agent_id:
        _agent_configs.pop(agent_id, None)
    else:
        _agent_configs.clear()


def _is_truncated(text: str) -> bool:
    if not text:
        return False
    text = text.strip()
    if text.endswith(("…", "...", "…", "。", "，", "：", "：")):
        return False
    if text.endswith((".", "!", "?", "！", "？", "】", "}", "]", ")", "`")):
        return False
    if len(text) < 50:
        return False
    last_50 = text[-50:]
    if last_50.count("{") != last_50.count("}"):
        return True
    if last_50.count("[") != last_50.count("]"):
        return True
    if last_50.count("```") % 2 != 0:
        return True
    return False


async def get_llm_reply(
    user_message: str,
    history: list[dict] | None = None,
    system_prompt: str | None = None,
    model: str | None = None,
    agent_id: str | None = None,
) -> str:
    if agent_id:
        llm_cfg = get_agent_llm_config(agent_id)
    else:
        llm_cfg = {
            "api_url": settings.llm_api_url,
            "api_key": settings.llm_api_key,
            "model": settings.llm_model,
            "max_tokens": 300,
            "temperature": 0.7,
        }

    api_url = llm_cfg["api_url"]
    api_key = llm_cfg["api_key"]
    use_model = model or llm_cfg["model"]
    max_tokens = llm_cfg["max_tokens"]
    temperature = llm_cfg["temperature"]

    system_prompt = system_prompt or (
        "你是太子，AI朝廷中的消息分拣官。你的职责是友好地回答用户的闲聊问题。"
        "如果用户的问题涉及具体任务或指令，建议他们使用'下旨'功能。"
        "回答要简洁友好，不超过100字。"
    )

    messages = [{"role": "system", "content": system_prompt}]
    if history:
        for h in history[-6:]:
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": user_message})

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{api_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": use_model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()

            if _is_truncated(content):
                content += "\n\n[输出因长度限制被截断，如需完整内容请告知继续]"

            return content
    except Exception as e:
        logger.error(f"LLM call failed for agent={agent_id} model={use_model}: {e}")
        return "臣暂无法回应，请稍后再试。"


async def stream_llm_reply(
    user_message: str,
    history: list[dict] | None = None,
    system_prompt: str | None = None,
    model: str | None = None,
    agent_id: str | None = None,
) -> AsyncGenerator[str, None]:
    if agent_id:
        llm_cfg = get_agent_llm_config(agent_id)
    else:
        llm_cfg = {
            "api_url": settings.llm_api_url,
            "api_key": settings.llm_api_key,
            "model": settings.llm_model,
            "max_tokens": 300,
            "temperature": 0.7,
        }

    api_url = llm_cfg["api_url"]
    api_key = llm_cfg["api_key"]
    use_model = model or llm_cfg["model"]
    max_tokens = llm_cfg["max_tokens"]
    temperature = llm_cfg["temperature"]

    system_prompt = system_prompt or (
        "你是太子，AI朝廷中的消息分拣官。你的职责是友好地回答用户的闲聊问题。"
        "如果用户的问题涉及具体任务或指令，建议他们使用'下旨'功能。"
        "回答要简洁友好，不超过100字。"
    )

    messages = [{"role": "system", "content": system_prompt}]
    if history:
        for h in history[-6:]:
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": user_message})

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{api_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": use_model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "stream": True,
                },
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        logger.error(f"LLM stream failed for agent={agent_id} model={use_model}: {e}")
        yield "臣暂无法回应，请稍后再试。"
