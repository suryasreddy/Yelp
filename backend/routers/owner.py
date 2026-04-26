from fastapi import APIRouter, Depends, HTTPException
from typing import List
from database import get_db
import schemas
from auth import get_current_user

router = APIRouter(prefix="/owner", tags=["Owner"])


def _strip_mongo_id(doc):
    if isinstance(doc, list):
        return [_strip_mongo_id(item) for item in doc]
    if isinstance(doc, dict):
        clean = dict(doc)
        clean.pop("_id", None)
        return clean
    return doc


def _require_owner(current_user: dict):
    if current_user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Owner access required")


@router.get("/dashboard")
def owner_dashboard(
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _require_owner(current_user)

    restaurants = list(db.restaurants.find({"claimed_by": current_user["id"]}))
    restaurant_ids = [r["id"] for r in restaurants]
    reviews = list(db.reviews.find({"restaurant_id": {"$in": restaurant_ids}})) if restaurant_ids else []
    total_reviews = len(reviews)
    rating_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in reviews:
        if r.get("rating") in rating_dist:
            rating_dist[r["rating"]] += 1
    recent_reviews = sorted(reviews, key=lambda x: x.get("created_at"), reverse=True)[:10]

    return {
        "restaurants": _strip_mongo_id(restaurants),
        "total_reviews": total_reviews,
        "rating_distribution": rating_dist,
        "recent_reviews": _strip_mongo_id(recent_reviews),
    }


@router.get("/restaurants", response_model=List[schemas.RestaurantOut])
def get_my_restaurants(
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _require_owner(current_user)
    return _strip_mongo_id(list(db.restaurants.find({"claimed_by": current_user["id"]})))


@router.get("/restaurants/{restaurant_id}/reviews", response_model=List[schemas.ReviewOut])
def get_restaurant_reviews(
    restaurant_id: int,
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _require_owner(current_user)
    restaurant = db.restaurants.find_one({"id": restaurant_id, "claimed_by": current_user["id"]})
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found or not claimed by you")
    return _strip_mongo_id(list(db.reviews.find({"restaurant_id": restaurant_id}).sort("created_at", -1)))
