from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from database import get_db
from database import get_next_id
import schemas
from auth import get_current_user
import os, shutil, uuid
from config import settings

router = APIRouter(prefix="/users", tags=["Users"])


def _strip_mongo_id(doc):
    if isinstance(doc, list):
        return [_strip_mongo_id(item) for item in doc]
    if isinstance(doc, dict):
        clean = dict(doc)
        clean.pop("_id", None)
        return clean
    return doc


def _save_upload(file: UploadFile, subfolder: str = "profile") -> str:
    os.makedirs(f"{settings.UPLOAD_DIR}/{subfolder}", exist_ok=True)
    ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4()}{ext}"
    path = f"{settings.UPLOAD_DIR}/{subfolder}/{filename}"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return f"/uploads/{subfolder}/{filename}"


@router.get("/me", response_model=schemas.UserOut)
def get_me(current_user: dict = Depends(get_current_user)):
    return _strip_mongo_id(current_user)


@router.put("/me", response_model=schemas.UserOut)
def update_me(
    payload: schemas.UserUpdate,
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    updates = payload.model_dump(exclude_unset=True)
    if updates:
        db.users.update_one({"id": current_user["id"]}, {"$set": updates})
    return _strip_mongo_id(db.users.find_one({"id": current_user["id"]}))


@router.post("/me/photo", response_model=schemas.UserOut)
def upload_profile_photo(
    file: UploadFile = File(...),
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    url = _save_upload(file, "profile")
    db.users.update_one({"id": current_user["id"]}, {"$set": {"profile_picture": url}})
    return _strip_mongo_id(db.users.find_one({"id": current_user["id"]}))


@router.get("/me/preferences", response_model=schemas.PreferencesOut)
def get_preferences(
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    prefs = db.user_preferences.find_one({"user_id": current_user["id"]})
    if not prefs:
        prefs = {
            "id": get_next_id(db, "user_preferences"),
            "user_id": current_user["id"],
            "cuisine_preferences": [],
            "price_range": None,
            "preferred_location": None,
            "search_radius": 10,
            "dietary_needs": [],
            "ambiance_preferences": [],
            "sort_preference": "rating",
        }
        db.user_preferences.insert_one(prefs)
    elif "id" not in prefs:
        prefs["id"] = get_next_id(db, "user_preferences")
        db.user_preferences.update_one({"_id": prefs["_id"]}, {"$set": {"id": prefs["id"]}})
    return _strip_mongo_id(prefs)


@router.put("/me/preferences", response_model=schemas.PreferencesOut)
def update_preferences(
    payload: schemas.PreferencesCreate,
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    db.user_preferences.update_one(
        {"user_id": current_user["id"]},
        {
            "$set": {
                **payload.model_dump(exclude_unset=True),
                "user_id": current_user["id"],
            },
            "$setOnInsert": {
                "id": get_next_id(db, "user_preferences"),
            },
        },
        upsert=True,
    )
    prefs = db.user_preferences.find_one({"user_id": current_user["id"]})
    if "id" not in prefs:
        prefs["id"] = get_next_id(db, "user_preferences")
        db.user_preferences.update_one({"_id": prefs["_id"]}, {"$set": {"id": prefs["id"]}})
    return _strip_mongo_id(prefs)


@router.get("/me/history")
def get_history(
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    reviews = list(db.reviews.find({"user_id": current_user["id"]}).sort("created_at", -1))
    added = list(db.restaurants.find({"added_by": current_user["id"]}).sort("created_at", -1))
    for r in reviews:
        r.setdefault("photos", [])
    for a in added:
        a.setdefault("photos", [])
    return {
        "reviews": _strip_mongo_id(reviews),
        "added_restaurants": _strip_mongo_id(added),
    }
