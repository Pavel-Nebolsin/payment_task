"""
FastStream-приложение consumer-сервиса.

Приложение регистрирует подписчиков бизнес-логики (`payments.new`, `payments.dead`),
которые при старте сами объявляют очередь `payments.new` и биндят её к exchange `payments`,
а также очередь `payments.dead`. Дополнительно объявляет exchange `payments.dlx` и
биндинг `payments.dead -> payments.dlx`, чтобы реджекнутые из payments.new сообщения
долетали до DLQ.
"""

from faststream import FastStream

# Импорт регистрирует подписчиков payments.new и payments.dead на broker
from app.messaging import consumer  # noqa: F401
from app.messaging.broker import broker, payments_dead_queue, payments_dlx_exchange

app = FastStream(broker)


@app.after_startup
async def setup() -> None:
    # payments.new/payments.dead уже объявлены и забиндены подписчиками.
    # Дополнительно объявляем DLX-обменник и биндим к нему DLQ.
    dlx_exchange = await broker.declare_exchange(payments_dlx_exchange)
    dead_queue = await broker.declare_queue(payments_dead_queue)
    await dead_queue.bind(dlx_exchange, routing_key="payments.dead")
