import json
import logging
from datetime import datetime, timezone
from kafka import KafkaConsumer
from database import get_mongo_db
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("review_worker")


def _now():
    return datetime.now(timezone.utc)


def _recalculate_rating(db, restaurant_id: int):
    reviews = list(db.reviews.find({"restaurant_id": restaurant_id}))
    count = len(reviews)
    avg = round(sum(r.get("rating", 0) for r in reviews) / count, 2) if count else 0.0
    db.restaurants.update_one({"id": restaurant_id}, {"$set": {"average_rating": avg, "review_count": count}})


def _process(db, topic: str, event: dict):
    payload = event.get("payload", {})
    if topic == "review.created":
        rid = int(payload["review_id"])
        existing = db.reviews.find_one({"id": rid})
        if not existing:
            db.reviews.insert_one(
                {
                    "id": rid,
                    "restaurant_id": int(payload["restaurant_id"]),
                    "user_id": int(payload["user_id"]),
                    "rating": int(payload["rating"]),
                    "comment": payload.get("comment"),
                    "photos": [],
                    "created_at": _now(),
                    "updated_at": _now(),
                }
            )
            _recalculate_rating(db, int(payload["restaurant_id"]))
        return rid
    if topic == "review.updated":
        rid = int(payload["review_id"])
        updates = payload.get("updates", {})
        if updates:
            updates["updated_at"] = _now()
            db.reviews.update_one({"id": rid, "restaurant_id": int(payload["restaurant_id"])}, {"$set": updates})
            _recalculate_rating(db, int(payload["restaurant_id"]))
        return rid
    if topic == "review.deleted":
        rid = int(payload["review_id"])
        db.reviews.delete_one({"id": rid, "restaurant_id": int(payload["restaurant_id"])})
        _recalculate_rating(db, int(payload["restaurant_id"]))
        return rid
    return None


def run():
    db = get_mongo_db()
    consumer = KafkaConsumer(
        "review.created",
        "review.updated",
        "review.deleted",
        bootstrap_servers=[x.strip() for x in settings.KAFKA_BOOTSTRAP_SERVERS.split(",") if x.strip()],
        group_id="review-worker-group",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    )
    logger.info("Review worker listening to review topics")
    for message in consumer:
        topic = message.topic
        event = message.value
        try:
            review_id = _process(db, topic, event)
            db.activity_logs.insert_one(
                {
                    "type": topic,
                    "status": "processed",
                    "entity_id": review_id,
                    "event": event,
                    "created_at": _now(),
                }
            )
            logger.info("Processed topic=%s review_id=%s", topic, review_id)
        except Exception as exc:
            db.activity_logs.insert_one(
                {
                    "type": topic,
                    "status": "failed",
                    "entity_id": event.get("entity_id"),
                    "event": event,
                    "error": str(exc),
                    "created_at": _now(),
                }
            )
            logger.exception("Failed topic=%s", topic)


if __name__ == "__main__":
    run()
