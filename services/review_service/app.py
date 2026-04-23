import uuid
from fastapi import FastAPI, Depends, HTTPException
from services.shared.schemas import ReviewCreate, ReviewUpdate
from services.shared.mongo import get_db, now_utc
from services.shared.http_auth import get_current_user
from services.shared.kafka_bus import publish_event


app = FastAPI(title="Review Service", version="2.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "review"}


@app.get("/restaurants/{restaurant_id}/reviews")
def list_reviews(restaurant_id: str, skip: int = 0, limit: int = 50):
    db = get_db()
    if not db.restaurants.find_one({"_id": restaurant_id}):
        raise HTTPException(status_code=404, detail="Restaurant not found")
    rows = list(db.reviews.find({"restaurant_id": restaurant_id}).sort("created_at", -1).skip(skip).limit(limit))
    for row in rows:
        row["id"] = row["_id"]
    return rows


@app.post("/restaurants/{restaurant_id}/reviews", status_code=202)
def create_review(restaurant_id: str, payload: ReviewCreate, current_user: dict = Depends(get_current_user)):
    db = get_db()
    if not db.restaurants.find_one({"_id": restaurant_id}):
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if db.reviews.find_one({"restaurant_id": restaurant_id, "user_id": current_user["_id"]}):
        raise HTTPException(status_code=400, detail="You already reviewed this restaurant")
    review_id = str(uuid.uuid4())
    event_payload = {
        "review_id": review_id,
        "restaurant_id": restaurant_id,
        "user_id": current_user["_id"],
        "rating": payload.rating,
        "comment": payload.comment,
    }
    try:
        event = publish_event("review.created", "review.created", current_user["_id"], review_id, event_payload)
    except Exception:
        raise HTTPException(status_code=503, detail="Kafka unavailable, review not queued")
    db.activity_logs.insert_one({"type": "review.created", "status": "queued", "entity_id": review_id, "event": event, "created_at": now_utc()})
    return {"status": "queued", "review_id": review_id}


@app.put("/restaurants/{restaurant_id}/reviews/{review_id}", status_code=202)
def update_review(restaurant_id: str, review_id: str, payload: ReviewUpdate, current_user: dict = Depends(get_current_user)):
    db = get_db()
    review = db.reviews.find_one({"_id": review_id, "restaurant_id": restaurant_id})
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    if review.get("user_id") != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    updates = payload.model_dump(exclude_none=True)
    try:
        event = publish_event(
            "review.updated",
            "review.updated",
            current_user["_id"],
            review_id,
            {"review_id": review_id, "restaurant_id": restaurant_id, "updates": updates},
        )
    except Exception:
        raise HTTPException(status_code=503, detail="Kafka unavailable, review update not queued")
    db.activity_logs.insert_one({"type": "review.updated", "status": "queued", "entity_id": review_id, "event": event, "created_at": now_utc()})
    return {"status": "queued", "review_id": review_id}


@app.delete("/restaurants/{restaurant_id}/reviews/{review_id}", status_code=202)
def delete_review(restaurant_id: str, review_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    review = db.reviews.find_one({"_id": review_id, "restaurant_id": restaurant_id})
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    if review.get("user_id") != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    try:
        event = publish_event(
            "review.deleted",
            "review.deleted",
            current_user["_id"],
            review_id,
            {"review_id": review_id, "restaurant_id": restaurant_id},
        )
    except Exception:
        raise HTTPException(status_code=503, detail="Kafka unavailable, review delete not queued")
    db.activity_logs.insert_one({"type": "review.deleted", "status": "queued", "entity_id": review_id, "event": event, "created_at": now_utc()})
    return {"status": "queued", "review_id": review_id}


@app.get("/reviews/{review_id}/status")
def review_status(review_id: str):
    db = get_db()
    log = db.activity_logs.find_one({"entity_id": review_id}, sort=[("created_at", -1)])
    if not log:
        raise HTTPException(status_code=404, detail="No review activity found")
    return {"review_id": review_id, "status": log.get("status", "unknown"), "last_event": log.get("type")}
