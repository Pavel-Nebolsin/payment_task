from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфигурация сервиса, читается из переменных окружения / .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+asyncpg://payments:payments@postgres:5432/payments"
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"
    api_key: str = "super-secret-key"

    outbox_poll_interval: float = 1.0
    outbox_batch_size: int = 50

    webhook_timeout: float = 10.0
    webhook_hmac_secret: str = "optional-secret"


settings = Settings()
