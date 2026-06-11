import uuid
from datetime import datetime

from sqlalchemy import DateTime, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    amount: Mapped[float] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3))
    description: Mapped[str] = mapped_column(Text, default="")
    meta: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, server_default="{}")
    status: Mapped[str] = mapped_column(String(16), default="pending", server_default="pending")
    idempotency_key: Mapped[str] = mapped_column(String, unique=True, index=True)
    webhook_url: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    webhook_delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
