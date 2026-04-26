from datetime import datetime, timezone
import re
import os
import shutil
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from database import get_db, get_next_id
import schemas
from auth import get_current_user, get_optional_user
from config import settings
from kafka_bus import publish_event

router = APIRouter(prefix="/restaurants", tags=["Restaurants"])


def _save_upload(file: UploadFile, subfolder: str = "restaurants") -> str:
    os.makedirs(f"{settings.UPLOAD_DIR}/{subfolder}", exist_ok=True)
    ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4()}{ext}"
    path = f"{settings.UPLOAD_DIR}/{subfolder}/{filename}"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return f"/uploads/{subfolder}/{filename}"


def _recalculate_rating(db, restaurant_id: int):
    reviews = list(db.reviews.find({"restaurant_id": restaurant_id}))
    count = len(reviews)
    avg = round(sum(r.get("rating", 0) for r in reviews) / count, 2) if count else 0.0
    db.restaurants.update_one({"id": restaurant_id}, {"$set": {"average_rating": avg, "review_count": count}})


@router.get("", response_model=List[schemas.RestaurantOut])
def search_restaurants(
    q: Optional[str] = Query(None, description="Name or keyword search"),
    cuisine: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    price_tier: Optional[str] = Query(None),
    sort: Optional[str] = Query("rating"),
    skip: int = 0,
    limit: int = 20,
    db=Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_user),
):
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

    sort_map = {"rating": [("average_rating", -1)], "reviews": [("review_count", -1)], "newest": [("created_at", -1)]}
    restaurants = list(db.restaurants.find(query).sort(sort_map.get(sort, sort_map["rating"])).skip(skip).limit(limit))

    favorite_ids = set()
    if current_user:
        favs = list(db.favorites.find({"user_id": current_user["id"]}, {"restaurant_id": 1, "_id": 0}))
        favorite_ids = {f["restaurant_id"] for f in favs}

    for r in restaurants:
        r.setdefault("is_favorite", r["id"] in favorite_ids)
        r.setdefault("photos", [])
    return restaurants


@router.post("", response_model=schemas.RestaurantOut, status_code=201)
def create_restaurant(payload: schemas.RestaurantCreate, db=Depends(get_db), current_user: dict = Depends(get_current_user)):
    restaurant_id = get_next_id(db, "restaurants")
    row = {
        "id": restaurant_id,
        **payload.model_dump(),
        "photos": [],
        "average_rating": 0.0,
        "review_count": 0,
        "is_claimed": False,
        "claimed_by": None,
        "added_by": current_user["id"],
        "created_at": datetime.now(timezone.utc),
    }
    db.restaurants.insert_one(row)
    return row


@router.get("/{restaurant_id}", response_model=schemas.RestaurantOut)
def get_restaurant(restaurant_id: int, db=Depends(get_db), current_user: Optional[dict] = Depends(get_optional_user)):
    restaurant = db.restaurants.find_one({"id": restaurant_id})
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if current_user:
        fav = db.favorites.find_one({"user_id": current_user["id"], "restaurant_id": restaurant_id})
        restaurant["is_favorite"] = fav is not None
    else:
        restaurant["is_favorite"] = False
    restaurant.setdefault("photos", [])
    return restaurant


@router.put("/{restaurant_id}", response_model=schemas.RestaurantOut)
def update_restaurant(restaurant_id: int, payload: schemas.RestaurantUpdate, db=Depends(get_db), current_user: dict = Depends(get_current_user)):
    restaurant = db.restaurants.find_one({"id": restaurant_id})
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    is_owner = restaurant.get("claimed_by") == current_user["id"]
    is_adder = restaurant.get("added_by") == current_user["id"]
    if not (is_owner or is_adder):
        raise HTTPException(status_code=403, detail="Not authorized")
    updates = payload.model_dump(exclude_unset=True)
    if updates:
        db.restaurants.update_one({"id": restaurant_id}, {"$set": updates})
    return db.restaurants.find_one({"id": restaurant_id})


@router.post("/{restaurant_id}/photos")
def upload_restaurant_photo(restaurant_id: int, file: UploadFile = File(...), db=Depends(get_db), current_user: dict = Depends(get_current_user)):
    restaurant = db.restaurants.find_one({"id": restaurant_id})
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    url = _save_upload(file, "restaurants")
    photos = restaurant.get("photos") or []
    photos.append(url)
    db.restaurants.update_one({"id": restaurant_id}, {"$set": {"photos": photos}})
    return {"url": url}


@router.post("/{restaurant_id}/claim", response_model=schemas.RestaurantOut)
def claim_restaurant(restaurant_id: int, db=Depends(get_db), current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Only owners can claim restaurants")
    restaurant = db.restaurants.find_one({"id": restaurant_id})
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if restaurant.get("is_claimed"):
        raise HTTPException(status_code=400, detail="Restaurant already claimed")
    db.restaurants.update_one({"id": restaurant_id}, {"$set": {"is_claimed": True, "claimed_by": current_user["id"]}})
    return db.restaurants.find_one({"id": restaurant_id})


@router.get("/{restaurant_id}/reviews", response_model=List[schemas.ReviewOut])
def list_reviews(restaurant_id: int, skip: int = 0, limit: int = 50, db=Depends(get_db)):
    restaurant = db.restaurants.find_one({"id": restaurant_id})
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    reviews = list(db.reviews.find({"restaurant_id": restaurant_id}).sort("created_at", -1).skip(skip).limit(limit))
    for r in reviews:
        r.setdefault("photos", [])
        u = db.users.find_one({"id": r["user_id"]}, {"password_hash": 0, "_id": 0})
        if u:
            r["user"] = u
    return reviews


@router.post("/{restaurant_id}/reviews", status_code=202)
def create_review(restaurant_id: int, payload: schemas.ReviewCreate, db=Depends(get_db), current_user: dict = Depends(get_current_user)):
    restaurant = db.restaurants.find_one({"id": restaurant_id})
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if not settings.ALLOW_DUPLICATE_REVIEW_SUBMITS:
        existing = db.reviews.find_one({"user_id": current_user["id"], "restaurant_id": restaurant_id})
        if existing:
            raise HTTPException(status_code=400, detail="You already reviewed this restaurant")
    review_id = get_next_id(db, "reviews")
    event_payload = {"review_id": review_id, "restaurant_id": restaurant_id, "user_id": current_user["id"], "rating": payload.rating, "comment": payload.comment}
    try:
        event = publish_event("review.created", "review.created", current_user["id"], review_id, event_payload)
    except Exception:
        raise HTTPException(status_code=503, detail="Kafka unavailable, review not queued")
    db.activity_logs.insert_one({"type": "review.created", "status": "queued", "entity_id": review_id, "event": event, "created_at": datetime.now(timezone.utc)})
    return {
        "status": "queued",
        "event_type": "review.created",
        "review_id": review_id,
        "restaurant_id": restaurant_id,
        "user_id": current_user["id"],
        "message": "Review queued for asynchronous processing",
    }


@router.put("/{restaurant_id}/reviews/{review_id}", status_code=202)
def update_review(restaurant_id: int, review_id: int, payload: schemas.ReviewUpdate, db=Depends(get_db), current_user: dict = Depends(get_current_user)):
    review = db.reviews.find_one({"id": review_id, "restaurant_id": restaurant_id})
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    if review["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    updates = payload.model_dump(exclude_unset=True)
    try:
        event = publish_event("review.updated", "review.updated", current_user["id"], review_id, {"review_id": review_id, "restaurant_id": restaurant_id, "updates": updates})
    except Exception:
        raise HTTPException(status_code=503, detail="Kafka unavailable, review update not queued")
    db.activity_logs.insert_one({"type": "review.updated", "status": "queued", "entity_id": review_id, "event": event, "created_at": datetime.now(timezone.utc)})
    return {
        "status": "queued",
        "event_type": "review.updated",
        "review_id": review_id,
        "restaurant_id": restaurant_id,
        "user_id": current_user["id"],
        "message": "Review update queued for asynchronous processing",
    }


@router.delete("/{restaurant_id}/reviews/{review_id}", status_code=202)
def delete_review(restaurant_id: int, review_id: int, db=Depends(get_db), current_user: dict = Depends(get_current_user)):
    review = db.reviews.find_one({"id": review_id, "restaurant_id": restaurant_id})
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    if review["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    try:
        event = publish_event("review.deleted", "review.deleted", current_user["id"], review_id, {"review_id": review_id, "restaurant_id": restaurant_id})
    except Exception:
        raise HTTPException(status_code=503, detail="Kafka unavailable, review delete not queued")
    db.activity_logs.insert_one({"type": "review.deleted", "status": "queued", "entity_id": review_id, "event": event, "created_at": datetime.now(timezone.utc)})
    return {
        "status": "queued",
        "event_type": "review.deleted",
        "review_id": review_id,
        "restaurant_id": restaurant_id,
        "user_id": current_user["id"],
        "message": "Review delete queued for asynchronous processing",
    }


@router.post("/{restaurant_id}/reviews/{review_id}/photos")
def upload_review_photo(restaurant_id: int, review_id: int, file: UploadFile = File(...), db=Depends(get_db), current_user: dict = Depends(get_current_user)):
    review = db.reviews.find_one({"id": review_id, "restaurant_id": restaurant_id, "user_id": current_user["id"]})
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    url = _save_upload(file, "reviews")
    photos = review.get("photos") or []
    photos.append(url)
    db.reviews.update_one({"id": review_id}, {"$set": {"photos": photos}})
    return {"url": url}


@router.post("/{restaurant_id}/favorite", status_code=201)
def add_favorite(restaurant_id: int, db=Depends(get_db), current_user: dict = Depends(get_current_user)):
    restaurant = db.restaurants.find_one({"id": restaurant_id})
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    existing = db.favorites.find_one({"user_id": current_user["id"], "restaurant_id": restaurant_id})
    if existing:
        raise HTTPException(status_code=400, detail="Already in favorites")
    db.favorites.insert_one({"user_id": current_user["id"], "restaurant_id": restaurant_id, "created_at": datetime.now(timezone.utc)})
    return {"message": "Added to favorites"}


@router.delete("/{restaurant_id}/favorite", status_code=204)
def remove_favorite(restaurant_id: int, db=Depends(get_db), current_user: dict = Depends(get_current_user)):
    fav = db.favorites.find_one({"user_id": current_user["id"], "restaurant_id": restaurant_id})
    if not fav:
        raise HTTPException(status_code=404, detail="Not in favorites")
    db.favorites.delete_one({"_id": fav["_id"]})


@router.get("/favorites/me", response_model=List[schemas.RestaurantOut])
def get_my_favorites(db=Depends(get_db), current_user: dict = Depends(get_current_user)):
    favs = list(db.favorites.find({"user_id": current_user["id"]}))
    restaurant_ids = [f["restaurant_id"] for f in favs]
    rows = list(db.restaurants.find({"id": {"$in": restaurant_ids}}))
    for r in rows:
        r["is_favorite"] = True
    return rows


@router.get("/reviews/{review_id}/status")
def review_status(review_id: int, db=Depends(get_db)):
    log = db.activity_logs.find_one({"entity_id": review_id}, sort=[("created_at", -1)])
    if not log:
        raise HTTPException(status_code=404, detail="No review activity found")
    return {"review_id": review_id, "status": log.get("status", "unknown"), "last_event": log.get("type")}
