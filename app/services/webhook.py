"""Отправка webhook-уведомлений клиенту с ретраями."""

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings
from app.models.payment import Payment


def build_webhook_payload(payment: Payment) -> dict:
    """Формирует тело webhook-запроса по результату обработки платежа."""
    event = "payment.succeeded" if payment.status == "succeeded" else "payment.failed"
    return {
        "event": event,
        "payment_id": str(payment.id),
        "status": payment.status,
        # Decimal преобразуется в str, чтобы избежать бага с float.
        "amount": str(payment.amount),
        "currency": payment.currency,
        "metadata": payment.meta,
        "processed_at": payment.processed_at.isoformat() if payment.processed_at else None,
    }


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.HTTPError, httpx.HTTPStatusError)),
    reraise=True,
)
async def send_webhook_with_retry(payment: Payment) -> None:
    """Отправляет webhook на payment.webhook_url. После 3 неудачных попыток пробрасывает исключение."""
    async with httpx.AsyncClient(timeout=settings.webhook_timeout) as client:
        resp = await client.post(payment.webhook_url, json=build_webhook_payload(payment))
        resp.raise_for_status()
