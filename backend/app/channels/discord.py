import logging
import urllib.request
import urllib.error
import json

from app.channels.base import BaseChannel

logger = logging.getLogger(__name__)


class DiscordChannel:
    name = "discord"
    label = "Discord"
    icon = "🎮"

    def __init__(self, token: str = "", channel_id: str = ""):
        self.token = token
        self.channel_id = channel_id
        self.base_url = "https://discord.com/api/v10"

    async def send_message(
        self, session_id: str, content: str, attachments: list | None = None
    ) -> bool:
        if not self.token or not self.channel_id:
            logger.warning("Discord channel not configured")
            return False

        embed = {
            "title": f"旨意 {session_id[:8]}",
            "description": content[:2000],
            "color": 0xF5C842,
        }
        data = json.dumps({"embeds": [embed]}).encode()

        req = urllib.request.Request(
            f"{self.base_url}/channels/{self.channel_id}/messages",
            data=data,
            headers={
                "Authorization": f"Bot {self.token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception as e:
            logger.error(f"Discord send failed: {e}")
            return False

    async def receive_message(self, webhook_data: dict) -> dict:
        return {
            "session_id": webhook_data.get("id", ""),
            "content": webhook_data.get("content", ""),
            "user_id": webhook_data.get("author", {}).get("id", ""),
            "attachments": [
                {"url": a.get("url", ""), "filename": a.get("filename", "")}
                for a in webhook_data.get("attachments", [])
            ],
        }

    async def send_file(
        self, session_id: str, file_url: str, filename: str
    ) -> bool:
        return await self.send_message(session_id, f"📎 {filename}: {file_url}")
