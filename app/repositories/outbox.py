import uuid

from app.models.outbox import Outbox


def create_event(*, aggregate_type: str, aggregate_id: uuid.UUID, event_type: str, payload: dict) -> Outbox:
    """Создаёт ORM-объект Outbox"""
    return Outbox(
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        event_type=event_type,
        payload=payload,
    )
