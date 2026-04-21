import asyncio
import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select, update

from app.db import async_session
from app.models.outbox import OutboxEvent
from app.services.event_bus import EventBus, get_event_bus

logger = logging.getLogger(__name__)

BATCH_SIZE = 50
MAX_ATTEMPTS = 5


class OutboxRelay:
    def __init__(self):
        self.bus: EventBus | None = None
        self._running = False

    async def start(self):
        self.bus = await get_event_bus()
        self._running = True
        logger.info("OutboxRelay started")
        await self._relay_loop()

    async def stop(self):
        self._running = False

    async def _relay_loop(self):
        wait_time = 0.1
        while self._running:
            try:
                processed = await self._relay_cycle()
                if processed > 0:
                    wait_time = 0.1
                else:
                    wait_time = min(wait_time * 2, 5.0)
            except Exception as e:
                logger.error(f"Outbox relay error: {e}")
                wait_time = 5.0
            await asyncio.sleep(wait_time)

    async def _relay_cycle(self) -> int:
        async with async_session() as db:
            result = await db.execute(
                select(OutboxEvent)
                .where(OutboxEvent.published == False, OutboxEvent.attempts < MAX_ATTEMPTS)
                .order_by(OutboxEvent.id)
                .limit(BATCH_SIZE)
                .with_for_update(skip_locked=True)
            )
            events = result.scalars().all()

            for event in events:
                try:
                    payload = event.payload
                    if isinstance(payload, str):
                        payload = json.loads(payload)

                    await self.bus.publish(
                        topic=event.topic,
                        trace_id=event.trace_id,
                        event_type=event.event_type,
                        producer="outbox",
                        payload=payload,
                    )

                    event.published = True
                    event.attempts += 1
                    event.published_at = datetime.now(timezone.utc)
                    await db.commit()

                except Exception as e:
                    event.attempts += 1
                    event.last_error = str(e)[:500]
                    await db.commit()
                    logger.error(f"Outbox relay failed for event {event.id}: {e}")

            return len(events)


async def run_outbox_relay():
    relay = OutboxRelay()
    await relay.start()
