import uuid
from fastapi import FastAPI, Depends, HTTPException
from services.shared.schemas import UserSignup, UserLogin, Token, PreferencesCreate
from services.shared.mongo import get_db, now_utc
from services.shared.security import hash_password, verify_password, create_session_token
from services.shared.http_auth import get_current_user, sanitize_user
from services.shared.kafka_bus import publish_event


app = FastAPI(title="User Reviewer Service", version="2.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "user-reviewer"}


@app.post("/auth/signup", response_model=Token, status_code=201)
def signup(payload: UserSignup):
    db = get_db()
    if db.users.find_one({"email": payload.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    user_id = str(uuid.uuid4())
    created_at = now_utc()
    user_doc = {
        "_id": user_id,
        "name": payload.name,
        "email": payload.email,
        "password_hash": hash_password(payload.password),
        "role": payload.role,
        "restaurant_location": payload.restaurant_location,
        "created_at": created_at,
    }
    db.users.insert_one(user_doc)
    db.preferences.insert_one({"user_id": user_id, **PreferencesCreate().model_dump()})
    db.activity_logs.insert_one({"type": "user.created", "user_id": user_id, "created_at": created_at})
    publish_event("user.created", "user.created", user_id, user_id, {"email": payload.email, "role": payload.role})
    token = create_session_token(user_id)
    return {"access_token": token, "token_type": "bearer", "user": sanitize_user(user_doc)}


@app.post("/auth/login", response_model=Token)
def login(payload: UserLogin):
    db = get_db()
    user_doc = db.users.find_one({"email": payload.email})
    if not user_doc or not verify_password(payload.password, user_doc.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_session_token(user_doc["_id"])
    return {"access_token": token, "token_type": "bearer", "user": sanitize_user(user_doc)}


@app.get("/users/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return sanitize_user(current_user)


@app.put("/users/me")
def update_me(payload: dict, current_user: dict = Depends(get_current_user)):
    db = get_db()
    allowed = {"name", "phone", "about_me", "city", "country", "state", "languages", "gender"}
    updates = {k: v for k, v in payload.items() if k in allowed}
    if updates:
        db.users.update_one({"_id": current_user["_id"]}, {"$set": updates})
        db.activity_logs.insert_one({"type": "user.updated", "user_id": current_user["_id"], "changes": updates, "created_at": now_utc()})
        publish_event("user.updated", "user.updated", current_user["_id"], current_user["_id"], updates)
    user_doc = db.users.find_one({"_id": current_user["_id"]})
    return sanitize_user(user_doc)


@app.get("/users/me/preferences")
def get_preferences(current_user: dict = Depends(get_current_user)):
    db = get_db()
    prefs = db.preferences.find_one({"user_id": current_user["_id"]})
    if not prefs:
        prefs = {"user_id": current_user["_id"], **PreferencesCreate().model_dump()}
        db.preferences.insert_one(prefs)
    prefs["id"] = str(prefs.get("_id", ""))
    return prefs


@app.put("/users/me/preferences")
def update_preferences(payload: PreferencesCreate, current_user: dict = Depends(get_current_user)):
    db = get_db()
    db.preferences.update_one(
        {"user_id": current_user["_id"]},
        {"$set": payload.model_dump()},
        upsert=True,
    )
    prefs = db.preferences.find_one({"user_id": current_user["_id"]})
    prefs["id"] = str(prefs.get("_id", ""))
    return prefs


@app.get("/users/me/history")
def history(current_user: dict = Depends(get_current_user)):
    db = get_db()
    reviews = list(db.reviews.find({"user_id": current_user["_id"]}).sort("created_at", -1))
    added = list(db.restaurants.find({"added_by": current_user["_id"]}).sort("created_at", -1))
    for row in reviews:
        row["id"] = row["_id"]
    for row in added:
        row["id"] = row["_id"]
    return {"reviews": reviews, "added_restaurants": added}
