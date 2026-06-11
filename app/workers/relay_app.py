"""
FastStream-приложение outbox-relay сервиса.

Не содержит подписчиков: только подключается к брокеру и запускает
фоновую задачу relay_loop, которая поллит таблицу outbox и публикует
неотправленные события в exchange `payments`.
"""

import asyncio
import logging

from faststream import FastStream

from app.messaging.broker import broker
from app.messaging.relay import relay_loop

logger = logging.getLogger(__name__)

app = FastStream(broker)

_relay_task: asyncio.Task | None = None


@app.after_startup
async def setup() -> None:
    global _relay_task
    _relay_task = asyncio.create_task(relay_loop())
    logger.info("outbox relay started")


@app.after_shutdown
async def teardown() -> None:
    if _relay_task is not None:
        _relay_task.cancel()
