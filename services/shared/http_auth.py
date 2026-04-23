from fastapi import HTTPException, Request
from .security import validate_session_token
from .mongo import get_db


def get_current_user(request: Request):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = auth_header.split(" ", 1)[1]
    user_id = validate_session_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    db = get_db()
    user = db.users.find_one({"_id": user_id})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def sanitize_user(user_doc: dict):
    return {
        "id": user_doc["_id"],
        "name": user_doc.get("name"),
        "email": user_doc.get("email"),
        "role": user_doc.get("role", "user"),
        "phone": user_doc.get("phone"),
        "about_me": user_doc.get("about_me"),
        "city": user_doc.get("city"),
        "country": user_doc.get("country"),
        "state": user_doc.get("state"),
        "languages": user_doc.get("languages"),
        "gender": user_doc.get("gender"),
        "profile_picture": user_doc.get("profile_picture"),
        "restaurant_location": user_doc.get("restaurant_location"),
        "created_at": user_doc.get("created_at"),
    }
