from fastapi import FastAPI, Depends, HTTPException
from services.shared.mongo import get_db
from services.shared.http_auth import get_current_user


app = FastAPI(title="Restaurant Owner Service", version="2.0.0")


def require_owner(user: dict):
    if user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Owner access required")


@app.get("/health")
def health():
    return {"status": "ok", "service": "owner"}


@app.get("/owner/dashboard")
def dashboard(current_user: dict = Depends(get_current_user)):
    require_owner(current_user)
    db = get_db()
    restaurants = list(db.restaurants.find({"claimed_by": current_user["_id"]}))
    restaurant_ids = [r["_id"] for r in restaurants]
    reviews = list(db.reviews.find({"restaurant_id": {"$in": restaurant_ids}}))
    rating_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for review in reviews:
        rating = review.get("rating")
        if rating in rating_dist:
            rating_dist[rating] += 1
    recent_reviews = sorted(reviews, key=lambda r: r.get("created_at"), reverse=True)[:10]
    for row in restaurants:
        row["id"] = row["_id"]
    for row in recent_reviews:
        row["id"] = row["_id"]
    return {
        "restaurants": restaurants,
        "total_reviews": len(reviews),
        "rating_distribution": rating_dist,
        "recent_reviews": recent_reviews,
    }


@app.get("/owner/restaurants")
def owner_restaurants(current_user: dict = Depends(get_current_user)):
    require_owner(current_user)
    db = get_db()
    restaurants = list(db.restaurants.find({"claimed_by": current_user["_id"]}))
    for row in restaurants:
        row["id"] = row["_id"]
    return restaurants


@app.get("/owner/restaurants/{restaurant_id}/reviews")
def owner_reviews(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    require_owner(current_user)
    db = get_db()
    restaurant = db.restaurants.find_one({"_id": restaurant_id, "claimed_by": current_user["_id"]})
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found or not claimed by you")
    reviews = list(db.reviews.find({"restaurant_id": restaurant_id}).sort("created_at", -1))
    for row in reviews:
        row["id"] = row["_id"]
    return reviews
