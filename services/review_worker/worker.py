import json
import logging
from kafka import KafkaConsumer
from services.shared.config import settings
from services.shared.mongo import get_db, now_utc


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("review_worker")


def recalc_restaurant_rating(db, restaurant_id: str):
    reviews = list(db.reviews.find({"restaurant_id": restaurant_id}))
    count = len(reviews)
    avg = round(sum(r.get("rating", 0) for r in reviews) / count, 2) if count > 0 else 0.0
    db.restaurants.update_one({"_id": restaurant_id}, {"$set": {"average_rating": avg, "review_count": count}})


def process_event(db, topic: str, event: dict):
    payload = event.get("payload", {})
    if topic == "review.created":
        review_id = payload["review_id"]
        existing = db.reviews.find_one({"_id": review_id})
        if existing:
            return review_id
        db.reviews.insert_one(
            {
                "_id": review_id,
                "restaurant_id": payload["restaurant_id"],
                "user_id": payload["user_id"],
                "rating": payload["rating"],
                "comment": payload.get("comment"),
                "photos": [],
                "created_at": now_utc(),
                "updated_at": now_utc(),
            }
        )
        recalc_restaurant_rating(db, payload["restaurant_id"])
        return review_id
    if topic == "review.updated":
        review_id = payload["review_id"]
        updates = payload.get("updates", {})
        if updates:
            updates["updated_at"] = now_utc()
            db.reviews.update_one({"_id": review_id, "restaurant_id": payload["restaurant_id"]}, {"$set": updates})
            recalc_restaurant_rating(db, payload["restaurant_id"])
        return review_id
    if topic == "review.deleted":
        review_id = payload["review_id"]
        db.reviews.delete_one({"_id": review_id, "restaurant_id": payload["restaurant_id"]})
        recalc_restaurant_rating(db, payload["restaurant_id"])
        return review_id
    return ""


def run():
    db = get_db()
    consumer = KafkaConsumer(
        "review.created",
        "review.updated",
        "review.deleted",
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(","),
        group_id="review-worker-group",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    )
    logger.info("Review worker listening to review topics...")
    for message in consumer:
        topic = message.topic
        event = message.value
        try:
            review_id = process_event(db, topic, event)
            if review_id:
                db.activity_logs.insert_one(
                    {
                        "type": topic,
                        "status": "processed",
                        "entity_id": review_id,
                        "event": event,
                        "created_at": now_utc(),
                    }
                )
            logger.info("Processed topic=%s review_id=%s", topic, review_id)
        except Exception as exc:
            logger.exception("Failed processing topic=%s error=%s", topic, exc)
            db.activity_logs.insert_one(
                {
                    "type": topic,
                    "status": "failed",
                    "entity_id": event.get("entity_id"),
                    "event": event,
                    "error": str(exc),
                    "created_at": now_utc(),
                }
            )


if __name__ == "__main__":
    run()
