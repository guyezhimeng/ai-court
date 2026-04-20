from typing import Protocol, ClassVar, runtime_checkable


@runtime_checkable
class BaseChannel(Protocol):
    name: ClassVar[str]
    label: ClassVar[str]
    icon: ClassVar[str]

    async def send_message(
        self, session_id: str, content: str, attachments: list | None = None
    ) -> bool: ...

    async def receive_message(self, webhook_data: dict) -> dict: ...

    async def send_file(
        self, session_id: str, file_url: str, filename: str
    ) -> bool: ...
