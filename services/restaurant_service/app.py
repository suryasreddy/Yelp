import re
import uuid
from fastapi import FastAPI, Depends, HTTPException, Query
from services.shared.schemas import RestaurantCreate, RestaurantUpdate
from services.shared.mongo import get_db, now_utc
from services.shared.http_auth import get_current_user
from services.shared.kafka_bus import publish_event


app = FastAPI(title="Restaurant Service", version="2.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "restaurant"}


@app.get("/restaurants")
def search_restaurants(
    q: str | None = Query(None),
    cuisine: str | None = Query(None),
    city: str | None = Query(None),
    price_tier: str | None = Query(None),
    sort: str = Query("rating"),
    skip: int = 0,
    limit: int = 20,
):
    db = get_db()
    query = {}
    if q:
        query["$or"] = [
            {"name": {"$regex": re.escape(q), "$options": "i"}},
            {"cuisine_type": {"$regex": re.escape(q), "$options": "i"}},
            {"description": {"$regex": re.escape(q), "$options": "i"}},
        ]
    if cuisine:
        query["cuisine_type"] = {"$regex": re.escape(cuisine), "$options": "i"}
    if city:
        query["city"] = {"$regex": re.escape(city), "$options": "i"}
    if price_tier:
        query["price_tier"] = price_tier
    sort_map = {
        "rating": [("average_rating", -1)],
        "reviews": [("review_count", -1)],
        "newest": [("created_at", -1)],
    }
    rows = list(db.restaurants.find(query).sort(sort_map.get(sort, sort_map["rating"])).skip(skip).limit(limit))
    for row in rows:
        row["id"] = row["_id"]
        row.setdefault("is_favorite", False)
    return rows


@app.post("/restaurants", status_code=201)
def create_restaurant(payload: RestaurantCreate, current_user: dict = Depends(get_current_user)):
    db = get_db()
    restaurant_id = str(uuid.uuid4())
    row = {
        "_id": restaurant_id,
        **payload.model_dump(),
        "photos": [],
        "average_rating": 0.0,
        "review_count": 0,
        "is_claimed": False,
        "claimed_by": None,
        "added_by": current_user["_id"],
        "created_at": now_utc(),
    }
    db.restaurants.insert_one(row)
    db.activity_logs.insert_one({"type": "restaurant.created", "restaurant_id": restaurant_id, "user_id": current_user["_id"], "created_at": now_utc()})
    publish_event("restaurant.created", "restaurant.created", current_user["_id"], restaurant_id, payload.model_dump())
    row["id"] = row["_id"]
    return row


@app.get("/restaurants/{restaurant_id}")
def get_restaurant(restaurant_id: str):
    db = get_db()
    row = db.restaurants.find_one({"_id": restaurant_id})
    if not row:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    row["id"] = row["_id"]
    row.setdefault("is_favorite", False)
    return row


@app.put("/restaurants/{restaurant_id}")
def update_restaurant(restaurant_id: str, payload: RestaurantUpdate, current_user: dict = Depends(get_current_user)):
    db = get_db()
    row = db.restaurants.find_one({"_id": restaurant_id})
    if not row:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    is_owner = row.get("claimed_by") == current_user["_id"]
    is_adder = row.get("added_by") == current_user["_id"]
    if not (is_owner or is_adder):
        raise HTTPException(status_code=403, detail="Not authorized")
    updates = payload.model_dump(exclude_none=True)
    if updates:
        db.restaurants.update_one({"_id": restaurant_id}, {"$set": updates})
        publish_event("restaurant.updated", "restaurant.updated", current_user["_id"], restaurant_id, updates)
    row = db.restaurants.find_one({"_id": restaurant_id})
    row["id"] = row["_id"]
    return row


@app.post("/restaurants/{restaurant_id}/claim")
def claim_restaurant(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Only owners can claim restaurants")
    db = get_db()
    row = db.restaurants.find_one({"_id": restaurant_id})
    if not row:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if row.get("is_claimed"):
        raise HTTPException(status_code=400, detail="Restaurant already claimed")
    db.restaurants.update_one(
        {"_id": restaurant_id},
        {"$set": {"is_claimed": True, "claimed_by": current_user["_id"]}},
    )
    publish_event("restaurant.claimed", "restaurant.claimed", current_user["_id"], restaurant_id, {"claimed_by": current_user["_id"]})
    row = db.restaurants.find_one({"_id": restaurant_id})
    row["id"] = row["_id"]
    return row
