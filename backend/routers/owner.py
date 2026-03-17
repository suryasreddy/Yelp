from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from database import get_db
import models, schemas
from auth import get_current_user

router = APIRouter(prefix="/owner", tags=["Owner"])


def _require_owner(current_user: models.User):
    if current_user.role != models.UserRole.owner:
        raise HTTPException(status_code=403, detail="Owner access required")


@router.get("/dashboard")
def owner_dashboard(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _require_owner(current_user)

    restaurants = (
        db.query(models.Restaurant)
        .filter(models.Restaurant.claimed_by == current_user.id)
        .all()
    )
    restaurant_ids = [r.id for r in restaurants]

    total_reviews = 0
    rating_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    recent_reviews = []

    if restaurant_ids:
        total_reviews = (
            db.query(func.count(models.Review.id))
            .filter(models.Review.restaurant_id.in_(restaurant_ids))
            .scalar()
        )

        dist = (
            db.query(models.Review.rating, func.count(models.Review.id))
            .filter(models.Review.restaurant_id.in_(restaurant_ids))
            .group_by(models.Review.rating)
            .all()
        )
        for rating, count in dist:
            rating_dist[rating] = count

        recent = (
            db.query(models.Review)
            .filter(models.Review.restaurant_id.in_(restaurant_ids))
            .order_by(models.Review.created_at.desc())
            .limit(10)
            .all()
        )
        recent_reviews = [schemas.ReviewOut.model_validate(r) for r in recent]

    return {
        "restaurants": [schemas.RestaurantOut.model_validate(r) for r in restaurants],
        "total_reviews": total_reviews,
        "rating_distribution": rating_dist,
        "recent_reviews": recent_reviews,
    }


@router.get("/restaurants", response_model=List[schemas.RestaurantOut])
def get_my_restaurants(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _require_owner(current_user)
    restaurants = (
        db.query(models.Restaurant)
        .filter(models.Restaurant.claimed_by == current_user.id)
        .all()
    )
    return restaurants


@router.get("/restaurants/{restaurant_id}/reviews", response_model=List[schemas.ReviewOut])
def get_restaurant_reviews(
    restaurant_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _require_owner(current_user)
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.id == restaurant_id,
        models.Restaurant.claimed_by == current_user.id,
    ).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found or not claimed by you")

    reviews = (
        db.query(models.Review)
        .filter(models.Review.restaurant_id == restaurant_id)
        .order_by(models.Review.created_at.desc())
        .all()
    )
    return reviews
