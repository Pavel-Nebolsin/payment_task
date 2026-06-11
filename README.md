# Payment Service

Асинхронный сервис процессинга платежей: принимает запрос на оплату,
обрабатывает его через эмулируемый платёжный шлюз и уведомляет клиента
о результате через webhook. Реализованы outbox pattern для гарантированной
публикации событий, идемпотентность на уровне API и консюмера, ретраи
с экспоненциальной задержкой и DLQ для недоставленных уведомлений (webhook).

## Архитектура

### Компоненты (6 сервисов в docker-compose)

1. **api** - FastAPI-приложение. Принимает запросы, валидирует, в одной
   транзакции пишет платёж (`status=pending`) и событие в `outbox`.
2. **consumer** - FastStream-приложение с подписчиками:
   - на очередь `payments.new`, тут вся бизнес-логика обработки платежа и
     доставки webhook;
   - на `payments.dead` - очередь "мёртвых" сообщений.
3. **relay** - отдельное FastStream-приложение, без подписчиков. Содержит
   только фоновую задачу **outbox relay** (стартует через хук `after_startup`),
   которая поллит таблицу `outbox` и публикует события в RabbitMQ.
4. **postgres** - БД (`payments`, `outbox`).
5. **rabbitmq** - брокер сообщений.
6. **migrate** - контейнер, выполняет миграции в БД и завершается.


### Поток данных

1. Клиент отправляет пост-запрос на `/api/v1/payments` с `X-API-Key` и `Idempotency-Key`.
2. API проверяет `Idempotency-Key`, если платёж с таким ключом уже есть, то
   возвращает существующий (`200 OK`), иначе создаёт новый (`202 Accepted`).
3. В одной транзакции: `INSERT` платежа + `INSERT` записи
   в `outbox`
4. Outbox relay читает неопубликованные строки (`published_at IS NULL`), публикует их и проставляет `published_at`.
5. Consumer получает сообщение из `payments.new`.
6. Если платёж уже в финальном статусе
   (`succeeded` или`failed`), то эмуляция обработки платежа пропускается.
7. Эмуляция платёжного шлюза (2-5 сек, 90% успех, 10% ошибка)
8. `UPDATE status, processed_at`, коммит.
9. Отправка webhook на `webhook_url` с ретраями (3 попытки, и экспоненциальная
   задержка). При успехе проставляется `webhook_delivered_at`.
10. Если webhook не доставлен после 3 попыток - происходит исключение, и 
   сообщение попадает в `payments.dead`.


### Идемпотентность

- **На уровне API**: `idempotency_key` - `UNIQUE` колонка. 
  Ловим `IntegrityError` вместо `select` перед `insert`.
- **На уровне консюмера**: проверяется текущий статус платежа
  (`SELECT ... FOR UPDATE`). Если он уже финальный, то повторная обработка
  сообщения не меняет состояние платежа.
- **На уровне вебхука**(в задании это не было): `webhook_delivered_at` повторная
  доставка одного и того же события не приведёт к повторной отправке webhook.


## Запуск

```bash
cp .env.example .env
docker compose up --build
```

Поднимутся 6 контейнров: 
`postgres` 
`rabbitmq`
`migrate` (завершится после миграций)
`api` (порт 8000)
`consumer` 
`relay`.


RabbitMQ Management UI: http://localhost:15672 (guest/guest).

## Как потестить

Можно через Swaggerна http://localhost:8000/docs (там же кнопка Authorize
для X-API-Key), либо curl-ом.

### Создать платёж

```bash
curl -i -X POST http://localhost:8000/api/v1/payments \
  -H "X-API-Key: super-secret-key" \
  -H "Idempotency-Key: 12345" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "100.00",
    "currency": "RUB",
    "description": "Order #123",
    "metadata": {"order_id": "123"},
    "webhook_url": "https://webhook.site/<your-uuid>"
  }'
```

Ответ `202 Accepted`:

```json
{"payment_id": "...", "status": "pending", "created_at": "..."}
```

Повторный запрос с тем же `Idempotency-Key` вернёт `200 OK` и тот же
`payment_id` (без повторного создания платежа).

### Получить платёж

```bash
curl http://localhost:8000/api/v1/payments/<payment_id> \
  -H "X-API-Key: super-secret-key"
```

Через 2-5 секунд после создания `status` сменится на `succeeded` или `failed`,
будет проставлен `processed_at`, а после успешной доставки webhook будет проставлен
`webhook_delivered_at`.

### Как принять webhook

Самое простое - взять одноразовый URL на https://webhook.site и подставить его
в `webhook_url`.

### Проверка очередей и DLQ

Откройте http://localhost:15672 (guest/guest), вкладка Queues. Там видны
`payments.new` и `payments.dead`, обменники `payments` / `payments.dlx`,
и количество сообщений.

Чтобы увидеть сообщение в `payments.dead`, создайте платёж с заведомо
недоступным `webhook_url` и дождитесь 3 неудачных попыток доставки,сообщение
будет реджектнуто и через DLX окажется в `payments.dead`.

## Конфигурация (`.env`)

| Переменная | Назначение |
|---|---|
| `DATABASE_URL` | строка подключения к PostgreSQL |
| `RABBITMQ_URL` | строка подключения к RabbitMQ |
| `API_KEY` | значение для заголовка `X-API-Key` |
| `OUTBOX_POLL_INTERVAL` | период опроса таблицы `outbox`, секунды |
| `OUTBOX_BATCH_SIZE` | размер пачки публикуемых событий за один тик |
| `WEBHOOK_TIMEOUT` | таймаут HTTP-запроса webhook, секунды |

## Некоторые особенности:

- `metadata` - зарезервированное имя в SQLAlchemy Declarative, поэтому атрибут
  модели платежа называется `meta`
- `amount` сериализуется в JSON как строка, чтобы не терять точность (баг с float числами)
- Сравнение `X-API-Key` константное по времени (для избежания тайминг-атак)
- В relay используется `FOR UPDATE SKIP LOCKED`, чтобы при нескольких
  воркерах не было дублирования публикации.
- контейнеры `consumer` и `relay` ждут пока поднимется `rabbitmq`, 
но иногда могут упасть из-за гонки с хелсчеками, поэтому добавлен `restart: on-failure`.
