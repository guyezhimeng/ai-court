import logging
import urllib.request
import json

from app.channels.base import BaseChannel

logger = logging.getLogger(__name__)


class FeishuChannel:
    name = "feishu"
    label = "飞书"
    icon = "🐦"

    def __init__(self, app_id: str = "", app_secret: str = ""):
        self.app_id = app_id
        self.app_secret = app_secret
        self._tenant_token = ""

    async def _get_tenant_token(self) -> str:
        if self._tenant_token:
            return self._tenant_token

        data = json.dumps({
            "app_id": self.app_id,
            "app_secret": self.app_secret,
        }).encode()

        req = urllib.request.Request(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read())
                self._tenant_token = result.get("tenant_access_token", "")
                return self._tenant_token
        except Exception as e:
            logger.error(f"Feishu auth failed: {e}")
            return ""

    async def send_message(
        self, session_id: str, content: str, attachments: list | None = None
    ) -> bool:
        if not self.app_id:
            return False
        logger.info(f"Feishu send to {session_id}: {content[:50]}")
        return True

    async def receive_message(self, webhook_data: dict) -> dict:
        event = webhook_data.get("event", {})
        return {
            "session_id": event.get("message", {}).get("chat_id", ""),
            "content": event.get("message", {}).get("content", ""),
            "user_id": event.get("sender", {}).get("sender_id", {}).get("user_id", ""),
            "attachments": [],
        }

    async def send_file(
        self, session_id: str, file_url: str, filename: str
    ) -> bool:
        return await self.send_message(session_id, f"📎 {filename}: {file_url}")
