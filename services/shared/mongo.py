from datetime import datetime, timezone
from pymongo import MongoClient, ASCENDING, TEXT
from .config import settings


_client = None
_db = None


def get_db():
    global _client, _db
    if _db is None:
        _client = MongoClient(settings.MONGODB_URL)
        _db = _client[settings.MONGODB_DB]
        _ensure_indexes(_db)
    return _db


def _ensure_indexes(db):
    db.users.create_index([("email", ASCENDING)], unique=True)
    db.sessions.create_index([("session_id", ASCENDING)], unique=True)
    db.sessions.create_index([("expiresAt", ASCENDING)], expireAfterSeconds=0)
    db.restaurants.create_index([("name", TEXT), ("cuisine_type", TEXT), ("description", TEXT)])
    db.restaurants.create_index([("city", ASCENDING)])
    db.reviews.create_index([("restaurant_id", ASCENDING), ("created_at", ASCENDING)])
    db.reviews.create_index([("user_id", ASCENDING), ("restaurant_id", ASCENDING)], unique=True)
    db.favourites.create_index([("user_id", ASCENDING), ("restaurant_id", ASCENDING)], unique=True)
    db.activity_logs.create_index([("created_at", ASCENDING)])


def now_utc():
    return datetime.now(timezone.utc)
