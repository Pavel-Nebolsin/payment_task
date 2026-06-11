from fastapi import FastAPI

from app.api.v1.payments import router as payments_router

app = FastAPI(title="Payment Service")

app.include_router(payments_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    """Healthcheck для докера."""
    return {"status": "ok"}
