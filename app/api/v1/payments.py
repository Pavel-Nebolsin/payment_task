import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_api_key
from app.schemas.payment import PaymentCreateRequest, PaymentCreateResponse, PaymentDetailResponse
from app.services import payment_service

router = APIRouter(
    prefix="/payments",
    tags=["payments"],
    dependencies=[Depends(require_api_key)],
)


@router.post("", response_model=PaymentCreateResponse)
async def create_payment(
    body: PaymentCreateRequest,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: AsyncSession = Depends(get_db),
) -> PaymentCreateResponse:
    if not idempotency_key:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Idempotency-Key header is required")

    result = await payment_service.create_payment(
        session,
        amount=body.amount,
        currency=body.currency.value,
        description=body.description,
        metadata=body.metadata,
        idempotency_key=idempotency_key,
        webhook_url=body.webhook_url,
    )

    response.status_code = status.HTTP_202_ACCEPTED if result.created else status.HTTP_200_OK

    payment = result.payment
    return PaymentCreateResponse(
        payment_id=payment.id,
        status=payment.status,
        created_at=payment.created_at,
    )


@router.get("/{payment_id}", response_model=PaymentDetailResponse)
async def get_payment(
    payment_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> PaymentDetailResponse:
    payment = await payment_service.get_payment(session, payment_id)
    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payment not found")

    return PaymentDetailResponse(
        payment_id=payment.id,
        amount=payment.amount,
        currency=payment.currency,
        description=payment.description,
        metadata=payment.meta,
        status=payment.status,
        webhook_url=payment.webhook_url,
        created_at=payment.created_at,
        processed_at=payment.processed_at,
        webhook_delivered_at=payment.webhook_delivered_at,
    )
