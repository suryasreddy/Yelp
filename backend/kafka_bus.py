import json
import uuid
from datetime import datetime, timezone
from kafka import KafkaProducer
from config import settings

_producer = None


def _get_producer():
    global _producer
    if _producer is None:
        _producer = KafkaProducer(
            bootstrap_servers=[x.strip() for x in settings.KAFKA_BOOTSTRAP_SERVERS.split(",") if x.strip()],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            retries=5,
            acks="all",
            linger_ms=20,
            client_id=settings.KAFKA_CLIENT_ID,
        )
    return _producer


def publish_event(topic: str, event_type: str, actor_user_id: int | None, entity_id: int | None, payload: dict):
    producer = _get_producer()
    event = {
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "correlation_id": str(uuid.uuid4()),
        "actor_user_id": actor_user_id,
        "entity_id": entity_id,
        "payload": payload,
    }
    producer.send(topic, event).get(timeout=10)
    return event
