import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment


async def get_by_id(session: AsyncSession, payment_id: uuid.UUID) -> Payment | None:
    """Возвращает платёж по id или None, если не найден."""
    return await session.get(Payment, payment_id)


async def get_for_update(session: AsyncSession, payment_id: uuid.UUID) -> Payment | None:
    """Загружает платёж."""
    result = await session.execute(select(Payment).where(Payment.id == payment_id).with_for_update())
    return result.scalar_one_or_none()


async def mark_webhook_delivered(session: AsyncSession, payment_id: uuid.UUID, delivered_at: datetime) -> None:
    """Проставляет webhook_delivered_at после успешной доставки вебхука."""
    payment = await session.get(Payment, payment_id)
    if payment is not None:
        payment.webhook_delivered_at = delivered_at


async def get_by_idempotency_key(session: AsyncSession, idempotency_key: str) -> Payment | None:
    """Возвращает платёж по idempotency_key или None, если не найден."""
    result = await session.execute(select(Payment).where(Payment.idempotency_key == idempotency_key))
    return result.scalar_one_or_none()


def create(
    *,
    amount,
    currency: str,
    description: str,
    meta: dict,
    idempotency_key: str,
    webhook_url: str,
) -> Payment:
    """Создаёт ORM-объект Payment."""
    return Payment(
        amount=amount,
        currency=currency,
        description=description,
        meta=meta,
        idempotency_key=idempotency_key,
        webhook_url=webhook_url,
    )
