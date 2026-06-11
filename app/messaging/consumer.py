"""Бизнес-логика обработки платежей"""

import asyncio
import logging
import random
from datetime import UTC, datetime

from faststream import Logger
from faststream.exceptions import RejectMessage
from faststream.middlewares.acknowledgement.config import AckPolicy

from app.db.session import async_session_maker
from app.messaging.broker import broker, payments_dead_queue, payments_exchange, payments_new_queue
from app.repositories import payment as payment_repo
from app.schemas.payment import PaymentCreatedEvent
from app.services.webhook import send_webhook_with_retry

logger = logging.getLogger(__name__)


async def emulate_gateway() -> str:
    """Эмулирует обработку платежа платёжным шлюзом"""
    await asyncio.sleep(random.uniform(2, 5))
    return "succeeded" if random.random() < 0.9 else "failed"


@broker.subscriber(
    payments_new_queue,
    payments_exchange,
    ack_policy=AckPolicy.REJECT_ON_ERROR,
)
async def handle_payment_created(event: PaymentCreatedEvent, logger: Logger) -> None:
    """
    Идемпотентный хендлер события payment.created.

    - Если платёж уже в терминальном статусе - обработку пропускаем.
    - Вебхук отправляется только если ещё не доставлен (webhook_delivered_at is None).
    - Если webhook не доставлен после retry он попадает в DLQ.
    """
    async with async_session_maker() as session:
        async with session.begin():
            payment = await payment_repo.get_for_update(session, event.payment_id)
            if payment is None:
                logger.error("payment %s not found, rejecting message", event.payment_id)
                raise RejectMessage()

            if payment.status == "pending":
                outcome = await emulate_gateway()
                payment.status = outcome
                payment.processed_at = datetime.now(UTC)
                logger.info("payment %s processed -> %s", payment.id, outcome)
            else:
                logger.info("payment %s already in terminal status %s, skip emulation", payment.id, payment.status)

        webhook_pending = payment.webhook_delivered_at is None
        payment_id = payment.id

    if not webhook_pending:
        return

    await send_webhook_with_retry(payment)

    async with async_session_maker() as session:
        async with session.begin():
            await payment_repo.mark_webhook_delivered(session, payment_id, datetime.now(UTC))


@broker.subscriber(payments_dead_queue)
async def handle_dead_letter(body: dict, logger: Logger) -> None:
    """Логирует факт попадания сообщения в payments.dead"""
    logger.warning("dead letter received: %s", body)
