from fastapi import APIRouter, Depends, HTTPException, status
from datetime import timedelta
from database import get_db
from database import get_next_id
import models, schemas
from auth import get_password_hash, verify_password, create_access_token
from config import settings
from datetime import datetime, timezone

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _public_user(user: dict):
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "phone": user.get("phone"),
        "about_me": user.get("about_me"),
        "city": user.get("city"),
        "country": user.get("country"),
        "state": user.get("state"),
        "languages": user.get("languages"),
        "gender": user.get("gender"),
        "profile_picture": user.get("profile_picture"),
        "restaurant_location": user.get("restaurant_location"),
        "created_at": user.get("created_at"),
    }


@router.post("/signup", response_model=schemas.Token, status_code=status.HTTP_201_CREATED)
def signup(payload: schemas.UserSignup, db=Depends(get_db)):
    existing = db.users.find_one({"email": payload.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = get_next_id(db, "users")
    user = {
        "id": user_id,
        "name": payload.name,
        "email": payload.email,
        "password_hash": get_password_hash(payload.password),
        "role": payload.role.value if hasattr(payload.role, "value") else str(payload.role),
        "restaurant_location": payload.restaurant_location,
        "created_at": datetime.now(timezone.utc),
    }
    db.users.insert_one(user)

    db.user_preferences.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "user_id": user_id,
                "cuisine_preferences": [],
                "price_range": None,
                "preferred_location": None,
                "search_radius": 10,
                "dietary_needs": [],
                "ambiance_preferences": [],
                "sort_preference": "rating",
            }
        },
        upsert=True,
    )

    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expires_at = datetime.now(timezone.utc) + expires_delta
    session_id = get_password_hash(f"{user_id}-{expires_at.isoformat()}")[:48]
    db.sessions.insert_one({"session_id": session_id, "user_id": user_id, "expires_at": expires_at})
    token = create_access_token(
        data={"sub": str(user_id), "sid": session_id},
        expires_delta=expires_delta,
    )
    return {"access_token": token, "token_type": "bearer", "user": _public_user(user)}


@router.post("/login", response_model=schemas.Token)
def login(payload: schemas.UserLogin, db=Depends(get_db)):
    user = db.users.find_one({"email": payload.email})
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expires_at = datetime.now(timezone.utc) + expires_delta
    session_id = get_password_hash(f"{user['id']}-{expires_at.isoformat()}")[:48]
    db.sessions.insert_one({"session_id": session_id, "user_id": user["id"], "expires_at": expires_at})
    token = create_access_token(
        data={"sub": str(user["id"]), "sid": session_id},
        expires_delta=expires_delta,
    )
    return {"access_token": token, "token_type": "bearer", "user": _public_user(user)}
