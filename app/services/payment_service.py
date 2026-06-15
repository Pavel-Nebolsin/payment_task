import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import outbox as outbox_repo
from app.repositories import payment as payment_repo
from app.models.payment import Payment


class PaymentResult:
    """Результат создания платежа."""

    def __init__(self, payment: Payment, created: bool) -> None:
        self.payment = payment
        self.created = created


async def create_payment(
    session: AsyncSession,
    *,
    amount: Decimal,
    currency: str,
    description: str,
    metadata: dict,
    idempotency_key: str,
    webhook_url: str,
) -> PaymentResult:
    """
    Создаёт платёж и запись в outbox в одной транзакции.

    Если платёж с таким idempotency_key уже существует (UNIQUE-констрейнт),
    откатывает транзакцию и возвращает уже существующий платёж.
    """
    payment = payment_repo.create(
        amount=amount,
        currency=currency,
        description=description,
        meta=metadata,
        idempotency_key=idempotency_key,
        webhook_url=webhook_url,
    )
    session.add(payment)

    try:
        # чтобы получить id платежа и поймать IntegrityError
        await session.flush()

        event = outbox_repo.create_event(
            aggregate_type="payment",
            aggregate_id=payment.id,
            event_type="payment.created",
            payload={
                "event_type": "payment.created",
                "payment_id": str(payment.id),
                "occurred_at": datetime.now(UTC).isoformat(),
            },
        )
        session.add(event)

        await session.commit()
        await session.refresh(payment)

    except IntegrityError:
        await session.rollback()
        existing = await payment_repo.get_by_idempotency_key(session, idempotency_key)
        if existing is None:
            raise
        return PaymentResult(payment=existing, created=False)

    return PaymentResult(payment=payment, created=True)


async def get_payment(session: AsyncSession, payment_id: uuid.UUID) -> Payment | None:
    """Возвращает платёж по id или None, если не найден."""
    return await payment_repo.get_by_id(session, payment_id)
