from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from auth import get_current_user
import os, shutil, uuid
from config import settings

router = APIRouter(prefix="/users", tags=["Users"])


def _save_upload(file: UploadFile, subfolder: str = "profile") -> str:
    os.makedirs(f"{settings.UPLOAD_DIR}/{subfolder}", exist_ok=True)
    ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4()}{ext}"
    path = f"{settings.UPLOAD_DIR}/{subfolder}/{filename}"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return f"/uploads/{subfolder}/{filename}"


@router.get("/me", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=schemas.UserOut)
def update_me(
    payload: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/me/photo", response_model=schemas.UserOut)
def upload_profile_photo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    url = _save_upload(file, "profile")
    current_user.profile_picture = url
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/me/preferences", response_model=schemas.PreferencesOut)
def get_preferences(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    prefs = db.query(models.UserPreferences).filter(
        models.UserPreferences.user_id == current_user.id
    ).first()
    if not prefs:
        prefs = models.UserPreferences(user_id=current_user.id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


@router.put("/me/preferences", response_model=schemas.PreferencesOut)
def update_preferences(
    payload: schemas.PreferencesCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    prefs = db.query(models.UserPreferences).filter(
        models.UserPreferences.user_id == current_user.id
    ).first()
    if not prefs:
        prefs = models.UserPreferences(user_id=current_user.id)
        db.add(prefs)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(prefs, field, value)
    db.commit()
    db.refresh(prefs)
    return prefs


@router.get("/me/history")
def get_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    reviews = (
        db.query(models.Review)
        .filter(models.Review.user_id == current_user.id)
        .order_by(models.Review.created_at.desc())
        .all()
    )
    added = (
        db.query(models.Restaurant)
        .filter(models.Restaurant.added_by == current_user.id)
        .order_by(models.Restaurant.created_at.desc())
        .all()
    )
    return {
        "reviews": [schemas.ReviewOut.model_validate(r) for r in reviews],
        "added_restaurants": [schemas.RestaurantOut.model_validate(r) for r in added],
    }
