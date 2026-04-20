import logging
from typing import Optional

from app.channels.base import BaseChannel

logger = logging.getLogger(__name__)


class WebChannel:
    name = "web"
    label = "内置聊天"
    icon = "💬"

    def __init__(self, ws_manager=None):
        self.ws_manager = ws_manager

    async def send_message(
        self, session_id: str, content: str, attachments: list | None = None
    ) -> bool:
        if self.ws_manager:
            await self.ws_manager.broadcast({
                "type": "chat.message",
                "session_id": session_id,
                "content": content,
                "attachments": attachments or [],
            })
        return True

    async def receive_message(self, webhook_data: dict) -> dict:
        return {
            "session_id": webhook_data.get("session_id", ""),
            "content": webhook_data.get("content", ""),
            "user_id": webhook_data.get("user_id", "default_user"),
            "attachments": webhook_data.get("attachments", []),
        }

    async def send_file(
        self, session_id: str, file_url: str, filename: str
    ) -> bool:
        if self.ws_manager:
            await self.ws_manager.broadcast({
                "type": "chat.file",
                "session_id": session_id,
                "file_url": file_url,
                "filename": filename,
            })
        return True
