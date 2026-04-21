import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

AGENTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "agents"

TOKEN_BUDGET = 8000
SOUL_CORE_MAX_TOKENS = 500
MEMORY_MAX_TOKENS = 800
HISTORY_MAX_MESSAGES = 10
SUMMARY_MAX_TOKENS = 200


class ContextOptimizer:
    def __init__(self):
        self._soul_cache: dict[str, dict] = {}
        if not AGENTS_DIR.exists():
            logger.error(
                f"AGENTS_DIR not found: {AGENTS_DIR}. "
                "All agent SOUL.md will be empty!"
            )

    def _estimate_tokens(self, text: str) -> int:
        cn_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        en_words = len(text.split()) - cn_chars
        return int(cn_chars / 1.5 + en_words / 0.75)

    def load_soul(self, agent_id: str) -> dict:
        if agent_id in self._soul_cache:
            return self._soul_cache[agent_id]

        soul_dir = AGENTS_DIR / agent_id
        soul_file = soul_dir / "SOUL.md"
        global_file = AGENTS_DIR / "GLOBAL.md"

        core = ""
        detailed = ""

        if soul_file.exists():
            content = soul_file.read_text(encoding="utf-8")
            parts = content.split("\n---\n", 1)
            core = parts[0].strip()
            detailed = parts[1].strip() if len(parts) > 1 else ""

        global_content = ""
        if global_file.exists():
            global_content = global_file.read_text(encoding="utf-8")

        group_content = ""
        group_name = self._get_group_for_agent(agent_id)
        if group_name:
            group_file = AGENTS_DIR / "groups" / f"{group_name}.md"
            if group_file.exists():
                group_content = group_file.read_text(encoding="utf-8")

        result = {
            "global": global_content,
            "group": group_content,
            "core": core,
            "detailed": detailed,
            "full_soul": f"{global_content}\n---\n{group_content}\n---\n{core}\n---\n{detailed}"
            if detailed
            else f"{global_content}\n---\n{group_content}\n---\n{core}",
        }
        self._soul_cache[agent_id] = result
        return result

    def _get_group_for_agent(self, agent_id: str) -> str | None:
        sansheng = {"taizi", "zhongshu", "menxia", "shangshu"}
        liubu = {"hubu", "libu", "bingbu", "xingbu", "gongbu", "libu_hr"}
        if agent_id in sansheng:
            return "sansheng"
        if agent_id in liubu:
            return "liubu"
        return None

    def build_system_prompt(
        self, agent_id: str, is_first_call: bool = True, summary: str = ""
    ) -> str:
        soul = self.load_soul(agent_id)
        parts = []

        if soul["global"]:
            parts.append(soul["global"])

        if soul["group"]:
            parts.append(soul["group"])

        parts.append(soul["core"])

        if is_first_call and soul["detailed"]:
            parts.append(soul["detailed"])
        elif summary:
            parts.append(f"[历史摘要]\n{summary}")

        return "\n---\n".join(parts)

    def compress_history(
        self, messages: list[dict], max_messages: int = HISTORY_MAX_MESSAGES
    ) -> tuple[list[dict], str]:
        if len(messages) <= max_messages:
            return messages, ""

        recent = messages[-max_messages:]
        older = messages[:-max_messages]

        summary_parts = []
        for msg in older:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:100]
            agent = msg.get("agent_id", "")
            if agent:
                summary_parts.append(f"[{agent}] {content}")
            else:
                summary_parts.append(f"[{role}] {content}")

        summary = "\n".join(summary_parts[-5:])
        if self._estimate_tokens(summary) > SUMMARY_MAX_TOKENS:
            summary = summary[: int(SUMMARY_MAX_TOKENS * 1.5)]

        return recent, summary

    def filter_memories(
        self, memories: list[dict], task_context: str, max_tokens: int = MEMORY_MAX_TOKENS
    ) -> list[dict]:
        if not memories:
            return []

        scored = []
        task_keywords = set(task_context.lower().split())

        for mem in memories:
            content = mem.get("content", "").lower()
            score = sum(1 for kw in task_keywords if kw in content)
            score += mem.get("importance", 0) * 0.1
            scored.append((score, mem))

        scored.sort(key=lambda x: x[0], reverse=True)

        result = []
        total_tokens = 0
        for score, mem in scored:
            mem_tokens = self._estimate_tokens(mem.get("content", ""))
            if total_tokens + mem_tokens > max_tokens:
                break
            result.append(mem)
            total_tokens += mem_tokens

        return result[:5]

    def build_enriched_message(
        self,
        original_message: str,
        task_context: str = "",
        memory_context: str = "",
        skills_context: str = "",
        reminder: str = "",
        token_budget: int = TOKEN_BUDGET,
    ) -> str:
        parts = [original_message]
        remaining = token_budget - self._estimate_tokens(original_message)

        if task_context and remaining > 200:
            tc_tokens = self._estimate_tokens(task_context)
            if tc_tokens > remaining * 0.4:
                task_context = task_context[: int(remaining * 0.4 * 1.5)]
            parts.append(f"\n---\n{task_context}")
            remaining -= self._estimate_tokens(task_context)

        if memory_context and remaining > 200:
            mem_tokens = self._estimate_tokens(memory_context)
            if mem_tokens > MEMORY_MAX_TOKENS:
                memory_context = memory_context[: int(MEMORY_MAX_TOKENS * 1.5)]
            parts.append(f"\n---\n{memory_context}")
            remaining -= self._estimate_tokens(memory_context)

        if skills_context and remaining > 200:
            parts.append(f"\n---\n{skills_context}")
            remaining -= self._estimate_tokens(skills_context)

        if reminder and remaining > 50:
            parts.append(f"\n{reminder}")

        return "".join(parts)

    def invalidate_cache(self, agent_id: str | None = None):
        if agent_id:
            self._soul_cache.pop(agent_id, None)
        else:
            self._soul_cache.clear()


context_optimizer = ContextOptimizer()
