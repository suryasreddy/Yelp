from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import List, Optional
from database import get_db
import models, schemas
from auth import get_current_user, get_optional_user
import os, shutil, uuid
from config import settings

router = APIRouter(prefix="/restaurants", tags=["Restaurants"])


def _save_upload(file: UploadFile, subfolder: str = "restaurants") -> str:
    os.makedirs(f"{settings.UPLOAD_DIR}/{subfolder}", exist_ok=True)
    ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4()}{ext}"
    path = f"{settings.UPLOAD_DIR}/{subfolder}/{filename}"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return f"/uploads/{subfolder}/{filename}"


def _recalculate_rating(restaurant: models.Restaurant, db: Session):
    result = db.query(
        func.avg(models.Review.rating), func.count(models.Review.id)
    ).filter(models.Review.restaurant_id == restaurant.id).first()
    restaurant.average_rating = round(float(result[0] or 0), 2)
    restaurant.review_count = result[1] or 0
    db.commit()


@router.get("", response_model=List[schemas.RestaurantOut])
def search_restaurants(
    q: Optional[str] = Query(None, description="Name or keyword search"),
    cuisine: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    price_tier: Optional[str] = Query(None),
    sort: Optional[str] = Query("rating"),
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_user),
):
    query = db.query(models.Restaurant)

    if q:
        search = f"%{q}%"
        query = query.filter(
            or_(
                models.Restaurant.name.ilike(search),
                models.Restaurant.cuisine_type.ilike(search),
                models.Restaurant.description.ilike(search),
            )
        )
    if cuisine:
        query = query.filter(models.Restaurant.cuisine_type.ilike(f"%{cuisine}%"))
    if city:
        query = query.filter(models.Restaurant.city.ilike(f"%{city}%"))
    if price_tier:
        query = query.filter(models.Restaurant.price_tier == price_tier)

    if sort == "rating":
        query = query.order_by(models.Restaurant.average_rating.desc())
    elif sort == "reviews":
        query = query.order_by(models.Restaurant.review_count.desc())
    elif sort == "newest":
        query = query.order_by(models.Restaurant.created_at.desc())
    else:
        query = query.order_by(models.Restaurant.average_rating.desc())

    restaurants = query.offset(skip).limit(limit).all()

    favorite_ids = set()
    if current_user:
        favs = db.query(models.Favorite.restaurant_id).filter(
            models.Favorite.user_id == current_user.id
        ).all()
        favorite_ids = {f[0] for f in favs}

    result = []
    for r in restaurants:
        out = schemas.RestaurantOut.model_validate(r)
        out.is_favorite = r.id in favorite_ids
        result.append(out)
    return result


@router.post("", response_model=schemas.RestaurantOut, status_code=201)
def create_restaurant(
    payload: schemas.RestaurantCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    restaurant = models.Restaurant(**payload.model_dump(), added_by=current_user.id)
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)
    return restaurant


@router.get("/{restaurant_id}", response_model=schemas.RestaurantOut)
def get_restaurant(
    restaurant_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_user),
):
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.id == restaurant_id
    ).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    out = schemas.RestaurantOut.model_validate(restaurant)
    if current_user:
        fav = db.query(models.Favorite).filter(
            models.Favorite.user_id == current_user.id,
            models.Favorite.restaurant_id == restaurant_id,
        ).first()
        out.is_favorite = fav is not None
    return out


@router.put("/{restaurant_id}", response_model=schemas.RestaurantOut)
def update_restaurant(
    restaurant_id: int,
    payload: schemas.RestaurantUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.id == restaurant_id
    ).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    # Must be owner or the one who added it
    is_owner = restaurant.claimed_by == current_user.id
    is_adder = restaurant.added_by == current_user.id
    if not (is_owner or is_adder):
        raise HTTPException(status_code=403, detail="Not authorized")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(restaurant, field, value)
    db.commit()
    db.refresh(restaurant)
    return restaurant


@router.post("/{restaurant_id}/photos")
def upload_restaurant_photo(
    restaurant_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.id == restaurant_id
    ).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    url = _save_upload(file, "restaurants")
    photos = restaurant.photos or []
    photos.append(url)
    restaurant.photos = photos
    db.commit()
    return {"url": url}


@router.post("/{restaurant_id}/claim", response_model=schemas.RestaurantOut)
def claim_restaurant(
    restaurant_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role != models.UserRole.owner:
        raise HTTPException(status_code=403, detail="Only owners can claim restaurants")

    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.id == restaurant_id
    ).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if restaurant.is_claimed:
        raise HTTPException(status_code=400, detail="Restaurant already claimed")

    restaurant.is_claimed = True
    restaurant.claimed_by = current_user.id
    db.commit()
    db.refresh(restaurant)
    return restaurant


# ─── Reviews ──────────────────────────────────────────────────────────────────

@router.get("/{restaurant_id}/reviews", response_model=List[schemas.ReviewOut])
def list_reviews(
    restaurant_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.id == restaurant_id
    ).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    reviews = (
        db.query(models.Review)
        .filter(models.Review.restaurant_id == restaurant_id)
        .order_by(models.Review.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return reviews


@router.post("/{restaurant_id}/reviews", response_model=schemas.ReviewOut, status_code=201)
def create_review(
    restaurant_id: int,
    payload: schemas.ReviewCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.id == restaurant_id
    ).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    existing = db.query(models.Review).filter(
        models.Review.user_id == current_user.id,
        models.Review.restaurant_id == restaurant_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You already reviewed this restaurant")

    review = models.Review(
        user_id=current_user.id,
        restaurant_id=restaurant_id,
        **payload.model_dump(),
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    _recalculate_rating(restaurant, db)
    return review


@router.put("/{restaurant_id}/reviews/{review_id}", response_model=schemas.ReviewOut)
def update_review(
    restaurant_id: int,
    review_id: int,
    payload: schemas.ReviewUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    review = db.query(models.Review).filter(
        models.Review.id == review_id,
        models.Review.restaurant_id == restaurant_id,
    ).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    if review.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(review, field, value)
    db.commit()
    db.refresh(review)

    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.id == restaurant_id
    ).first()
    _recalculate_rating(restaurant, db)
    return review


@router.delete("/{restaurant_id}/reviews/{review_id}", status_code=204)
def delete_review(
    restaurant_id: int,
    review_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    review = db.query(models.Review).filter(
        models.Review.id == review_id,
        models.Review.restaurant_id == restaurant_id,
    ).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    if review.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db.delete(review)
    db.commit()

    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.id == restaurant_id
    ).first()
    _recalculate_rating(restaurant, db)


@router.post("/{restaurant_id}/reviews/{review_id}/photos")
def upload_review_photo(
    restaurant_id: int,
    review_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    review = db.query(models.Review).filter(
        models.Review.id == review_id,
        models.Review.restaurant_id == restaurant_id,
        models.Review.user_id == current_user.id,
    ).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    os.makedirs(f"{settings.UPLOAD_DIR}/reviews", exist_ok=True)
    ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4()}{ext}"
    path = f"{settings.UPLOAD_DIR}/reviews/{filename}"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    url = f"/uploads/reviews/{filename}"

    photos = review.photos or []
    photos.append(url)
    review.photos = photos
    db.commit()
    return {"url": url}


# ─── Favorites ────────────────────────────────────────────────────────────────

@router.post("/{restaurant_id}/favorite", status_code=201)
def add_favorite(
    restaurant_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.id == restaurant_id
    ).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    existing = db.query(models.Favorite).filter(
        models.Favorite.user_id == current_user.id,
        models.Favorite.restaurant_id == restaurant_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already in favorites")

    fav = models.Favorite(user_id=current_user.id, restaurant_id=restaurant_id)
    db.add(fav)
    db.commit()
    return {"message": "Added to favorites"}


@router.delete("/{restaurant_id}/favorite", status_code=204)
def remove_favorite(
    restaurant_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    fav = db.query(models.Favorite).filter(
        models.Favorite.user_id == current_user.id,
        models.Favorite.restaurant_id == restaurant_id,
    ).first()
    if not fav:
        raise HTTPException(status_code=404, detail="Not in favorites")
    db.delete(fav)
    db.commit()


@router.get("/favorites/me", response_model=List[schemas.RestaurantOut])
def get_my_favorites(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    favs = (
        db.query(models.Restaurant)
        .join(models.Favorite)
        .filter(models.Favorite.user_id == current_user.id)
        .all()
    )
    result = []
    for r in favs:
        out = schemas.RestaurantOut.model_validate(r)
        out.is_favorite = True
        result.append(out)
    return result
