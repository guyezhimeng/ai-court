import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.event_bus import PUBSUB_PREFIX, get_event_bus

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active: dict[str, WebSocket] = {}

    async def connect(self, client_id: str, ws: WebSocket):
        await ws.accept()
        self.active[client_id] = ws

    def disconnect(self, client_id: str):
        self.active.pop(client_id, None)

    async def send_to(self, client_id: str, data: dict):
        ws = self.active.get(client_id)
        if ws:
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(client_id)

    async def broadcast(self, data: dict):
        dead = []
        for cid, ws in self.active.items():
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(cid)
        for cid in dead:
            self.disconnect(cid)


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    client_id = id(ws)
    await manager.connect(str(client_id), ws)

    bus = await get_event_bus()
    pubsub = await bus.subscribe_pubsub(["*"])

    async def relay_events():
        try:
            async for message in pubsub.listen():
                if message["type"] == "pmessage":
                    try:
                        data = json.loads(message["data"])
                        await ws.send_json(data)
                    except Exception:
                        pass
        except asyncio.CancelledError:
            pass

    relay_task = asyncio.create_task(relay_events())

    try:
        while True:
            data = await ws.receive_json()
            if data.get("type") == "ping":
                await ws.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        relay_task.cancel()
        manager.disconnect(str(client_id))
        try:
            await pubsub.unsubscribe()
        except Exception:
            pass
