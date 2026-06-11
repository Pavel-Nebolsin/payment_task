"""
Топология RabbitMQ.

- exchange `payments` - основной обменник для событий о платежах.
- queue `payments.new` - очередь обработки, настроена с DLX, чтобы
  реджекнутые сообщения уходили в payments.dlx -> payments.dead.
- exchange `payments.dlx`- dead-letter обменник.
- queue `payments.dead` - очередь "мёртвых" сообщений (DLQ).

Все объекты durable, сообщения публикуются как persistent (delivery_mode=2),
чтобы пережить рестарт брокера.
"""

from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange, RabbitQueue

from app.config import settings

broker = RabbitBroker(settings.rabbitmq_url)

# Основной обменник и очередь
payments_exchange = RabbitExchange("payments", type=ExchangeType.DIRECT, durable=True)

payments_new_queue = RabbitQueue(
    "payments.new",
    durable=True,
    routing_key="payments.new",
    arguments={
        "x-dead-letter-exchange": "payments.dlx",
        "x-dead-letter-routing-key": "payments.dead",
    },
)

# DLQ
payments_dlx_exchange = RabbitExchange("payments.dlx", type=ExchangeType.DIRECT, durable=True)

payments_dead_queue = RabbitQueue(
    "payments.dead",
    durable=True,
    routing_key="payments.dead",
)
