import json
import logging
from datetime import datetime
from typing import Any

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

TOPIC_TASK_CREATED = "task.created"
TOPIC_TASK_DISPATCH = "task.dispatch"
TOPIC_TASK_STATUS = "task.status"
TOPIC_TASK_COMPLETED = "task.completed"
TOPIC_TASK_STALLED = "task.stalled"
TOPIC_TASK_ESCALATED = "task.escalated"
TOPIC_AGENT_THOUGHTS = "agent.thoughts"
TOPIC_AGENT_HEARTBEAT = "agent.heartbeat"
TOPIC_CHAT_MESSAGE = "chat.message"

STREAM_PREFIX = "edict:stream:"
PUBSUB_PREFIX = "edict:pubsub:"


class EventBus:
    def __init__(self):
        self.redis: aioredis.Redis | None = None

    async def connect(self):
        self.redis = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=20,
        )
        logger.info("EventBus connected to Redis")

    async def close(self):
        if self.redis:
            await self.redis.close()
            logger.info("EventBus disconnected from Redis")

    async def publish(
        self,
        topic: str,
        trace_id: str,
        event_type: str,
        producer: str = "",
        payload: dict | None = None,
        meta: dict | None = None,
    ) -> str:
        if not self.redis:
            raise RuntimeError("EventBus not connected")

        event = {
            "topic": topic,
            "trace_id": trace_id,
            "event_type": event_type,
            "producer": producer,
            "payload": json.dumps(payload or {}, ensure_ascii=False),
            "meta": json.dumps(meta or {}, ensure_ascii=False),
            "timestamp": datetime.utcnow().isoformat(),
        }

        stream_key = f"{STREAM_PREFIX}{topic}"
        entry_id = await self.redis.xadd(stream_key, event, maxlen=10000)

        pubsub_key = f"{PUBSUB_PREFIX}{topic}"
        await self.redis.publish(pubsub_key, json.dumps(event, ensure_ascii=False))

        logger.debug(f"Event published: {topic}/{event_type} [{trace_id[:8]}]")
        return entry_id

    async def consume(
        self,
        topics: list[str],
        group: str,
        consumer: str,
        count: int = 10,
        block_ms: int = 5000,
    ) -> list[dict]:
        if not self.redis:
            raise RuntimeError("EventBus not connected")

        streams = {}
        for topic in topics:
            stream_key = f"{STREAM_PREFIX}{topic}"
            try:
                await self.redis.xgroup_create(stream_key, group, id="0", mkstream=True)
            except aioredis.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    raise
            streams[stream_key] = ">"

        if not streams:
            return []

        results = await self.redis.xreadgroup(
            group, consumer, streams, count=count, block=block_ms
        )

        events = []
        for stream_name, messages in results:
            for msg_id, data in messages:
                event = dict(data)
                event["_msg_id"] = msg_id
                event["_stream"] = stream_name
                if "payload" in event and isinstance(event["payload"], str):
                    try:
                        event["payload"] = json.loads(event["payload"])
                    except json.JSONDecodeError:
                        pass
                if "meta" in event and isinstance(event["meta"], str):
                    try:
                        event["meta"] = json.loads(event["meta"])
                    except json.JSONDecodeError:
                        pass
                events.append(event)

        return events

    async def ack(self, group: str, topic: str, msg_id: str):
        if not self.redis:
            return
        stream_key = f"{STREAM_PREFIX}{topic}"
        await self.redis.xack(stream_key, group, msg_id)

    async def subscribe_pubsub(self, topics: list[str]):
        if not self.redis:
            raise RuntimeError("EventBus not connected")
        pubsub = self.redis.pubsub()
        patterns = [f"{PUBSUB_PREFIX}{topic}" for topic in topics]
        await pubsub.psubscribe(*patterns)
        return pubsub


_event_bus: EventBus | None = None


async def get_event_bus() -> EventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
        await _event_bus.connect()
    return _event_bus
