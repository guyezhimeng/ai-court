import json
import logging

import httpx

from app.models.task import Task
from app.services.llm_service import get_agent_llm_config

logger = logging.getLogger(__name__)


class ReviewStrategy:

    _SENSITIVE_KEYWORDS = [
        "删除", "清空", "drop", "truncate", "remove all",
        "权限", "密码", "password", "root", "admin",
        "修改数据库", "覆盖", "替换全部",
    ]

    def decide_review_level(self, task: Task) -> str:
        description = task.description or ""
        title = task.title or ""

        if self._has_sensitive_keywords(description):
            logger.info(f"Task {task.trace_id}: sensitive keywords detected -> llm_deep")
            return "llm_deep"

        if len(description) < 20 or self._is_vague(description):
            logger.info(f"Task {task.trace_id}: vague description -> llm_standard")
            return "llm_standard"

        if task.subtasks and len(task.subtasks) >= 1:
            logger.info(f"Task {task.trace_id}: has subtasks -> rule_fast")
            return "rule_fast"

        return "llm_standard"

    def _has_sensitive_keywords(self, text: str) -> bool:
        text_lower = text.lower()
        return any(kw in text_lower for kw in self._SENSITIVE_KEYWORDS)

    def _is_vague(self, text: str) -> bool:
        if len(text) < 50:
            vague_starters = ["帮我", "做一个", "弄个", "搞个", "来个"]
            has_vague = any(text.startswith(s) for s in vague_starters)
            has_structure = any(c in text for c in ["：", ":", "1.", "步骤", "要求"])
            return has_vague and not has_structure
        return False

    async def execute_review(self, task: Task, level: str) -> dict:
        if level == "rule_fast":
            checks = {
                "has_description": bool(task.description and len(task.description) >= 10),
                "has_subtasks": bool(task.subtasks),
                "no_sensitive_keywords": not self._has_sensitive_keywords(task.description or ""),
            }
            if all(checks.values()):
                return {"result": "通过", "reason": "规则快速审核：任务描述清晰，有子任务拆解，无敏感操作", "level": "rule_fast"}
            else:
                failed = [k for k, v in checks.items() if not v]
                return {"result": "附条件通过", "reason": f"规则审核部分未通过：{', '.join(failed)}", "level": "rule_fast"}

        elif level == "llm_standard":
            return await self._llm_review(task, depth="standard")

        elif level == "llm_deep":
            return await self._llm_review(task, depth="deep")

        return {"result": "通过", "reason": "未知审核级别", "level": "unknown"}

    async def _llm_review(self, task: Task, depth: str) -> dict:
        llm_cfg = get_agent_llm_config("menxia")

        if depth == "deep":
            prompt = (
                "你是门下省审核官。请严格审核以下旨意，检查：\n"
                "1. 任务描述是否清晰完整\n"
                "2. 是否存在安全风险（数据删除、权限变更等）\n"
                "3. 是否可行\n"
                "4. 是否需要拆分为多个子任务\n\n"
                f"任务标题：{task.title}\n"
                f"任务描述：{task.description}\n"
                f"子任务：{json.dumps(task.subtasks, ensure_ascii=False) if task.subtasks else '无'}\n\n"
                "回复格式（严格遵守）：\n"
                "审核结果：通过 / 驳回 / 附条件通过\n"
                "审核意见：（一句话）\n"
                "如果驳回，原因和建议："
            )
        else:
            prompt = (
                "你是门下省审核官。快速审核以下旨意是否可以分配执行。\n\n"
                f"任务标题：{task.title}\n"
                f"任务描述：{task.description}\n\n"
                "回复格式（严格遵守）：\n"
                "审核结果：通过 / 驳回 / 附条件通过\n"
                "审核意见：（一句话）"
            )

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{llm_cfg['api_url']}/chat/completions",
                    headers={"Authorization": f"Bearer {llm_cfg['api_key']}"},
                    json={
                        "model": llm_cfg["model"],
                        "messages": [
                            {"role": "system", "content": "你是门下省审核官，回复必须严格遵守指定格式。"},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.3,
                        "max_tokens": 500,
                    },
                )
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"].strip()
                return {"result": content, "level": f"llm_{depth}"}
        except Exception as e:
            logger.error(f"门下省 LLM 审核失败: {e}")
            return {"result": "附条件通过", "reason": f"审核服务异常: {e}", "level": f"llm_{depth}"}


review_strategy = ReviewStrategy()
