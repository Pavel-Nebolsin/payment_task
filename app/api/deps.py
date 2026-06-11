from collections.abc import AsyncGenerator

from fastapi import Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import is_valid_api_key
from app.db.session import async_session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Выдаёт async-сессию БД."""
    async with async_session_maker() as session:
        yield session


async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Проверка X-API-Key. Без ключа или с неверным -> 401."""
    if x_api_key is None or not is_valid_api_key(x_api_key, settings.api_key):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")
