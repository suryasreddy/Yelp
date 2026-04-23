import json
import logging
import uuid
from datetime import datetime, timezone
from kafka import KafkaProducer
from .config import settings


logger = logging.getLogger("kafka_bus")
_producer = None


def get_producer():
    global _producer
    if _producer is None:
        _producer = KafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(","),
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            retries=5,
            acks="all",
            linger_ms=20,
            client_id=settings.KAFKA_CLIENT_ID,
        )
    return _producer


def publish_event(topic: str, event_type: str, actor_user_id: str, entity_id: str, payload: dict):
    producer = get_producer()
    event = {
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "correlation_id": str(uuid.uuid4()),
        "actor_user_id": actor_user_id,
        "entity_id": entity_id,
        "payload": payload,
    }
    future = producer.send(topic, event)
    future.get(timeout=10)
    logger.info("Published event topic=%s correlation_id=%s", topic, event["correlation_id"])
    return event
