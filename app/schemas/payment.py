import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, field_serializer


class Currency(str, Enum):
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class PaymentCreatedEvent(BaseModel):
    """Сообщение в очереди payments.new."""

    event_type: str
    payment_id: uuid.UUID
    occurred_at: datetime


class PaymentCreateRequest(BaseModel):
    """Тело запроса POST /api/v1/payments."""

    amount: Decimal = Field(gt=0)
    currency: Currency
    description: str = ""
    metadata: dict = Field(default_factory=dict)
    webhook_url: str


class PaymentCreateResponse(BaseModel):
    """Ответ 202/200 на создание платежа."""

    payment_id: uuid.UUID
    status: PaymentStatus
    created_at: datetime

    @field_serializer("payment_id")
    def serialize_payment_id(self, value: uuid.UUID) -> str:
        return str(value)


class PaymentDetailResponse(BaseModel):
    """Ответ GET /api/v1/payments/{payment_id}."""

    payment_id: uuid.UUID
    amount: Decimal
    currency: Currency
    description: str
    metadata: dict
    status: PaymentStatus
    webhook_url: str
    created_at: datetime
    processed_at: datetime | None
    webhook_delivered_at: datetime | None

    @field_serializer("payment_id")
    def serialize_payment_id(self, value: uuid.UUID) -> str:
        return str(value)

    # Decimal преобразуется в str, чтобы избежать бага с float.
    @field_serializer("amount")
    def serialize_amount(self, value: Decimal) -> str:
        return str(value)
