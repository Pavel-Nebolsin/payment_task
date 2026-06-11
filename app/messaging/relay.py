"""
Outbox relay, фоновая задача, публикующая неотправленные события из таблицы outbox в RabbitMQ.

"""

import asyncio
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import async_session_maker
from app.messaging.broker import broker, payments_exchange
from app.models.outbox import Outbox

logger = logging.getLogger(__name__)


async def relay_tick(session: AsyncSession) -> int:
    """Публикует пачку неотправленных событий и возвращает число опубликованных строк."""
    async with session.begin():
        rows = (
            (
                await session.execute(
                    select(Outbox)
                    .where(Outbox.published_at.is_(None))
                    .order_by(Outbox.created_at)
                    .limit(settings.outbox_batch_size)
                    .with_for_update(skip_locked=True)
                )
            )
            .scalars()
            .all()
        )

        for row in rows:
            await broker.publish(
                row.payload,
                exchange=payments_exchange,
                routing_key="payments.new",
                persist=True,
            )
            row.published_at = func.now()
            row.attempts += 1

    return len(rows)


async def relay_loop() -> None:
    """Бесконечный цикл поллинга outbox."""
    while True:
        try:
            async with async_session_maker() as session:
                published = await relay_tick(session)
                if published:
                    logger.info("outbox relay: published %d event(s)", published)
        except Exception:
            logger.exception("outbox relay: tick failed")

        await asyncio.sleep(settings.outbox_poll_interval)
