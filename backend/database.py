from pymongo import MongoClient, ASCENDING, TEXT
from pymongo.collection import ReturnDocument
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from config import settings

# Kept for compatibility with older SQLAlchemy models/imports in the repo.
# Lab 2 runtime uses MongoDB through get_db().
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)
Base = declarative_base()

_mongo_client = None
_mongo_db = None


def get_mongo_db():
    global _mongo_client, _mongo_db
    if _mongo_db is None:
        _mongo_client = MongoClient(settings.MONGODB_URL)
        _mongo_db = _mongo_client[settings.MONGODB_DB]
        _ensure_indexes(_mongo_db)
    return _mongo_db


def get_db():
    # Dependency for FastAPI routes: returns Mongo database handle.
    yield get_mongo_db()


def get_next_id(db, counter_name: str) -> int:
    row = db.counters.find_one_and_update(
        {"_id": counter_name},
        {"$inc": {"value": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return int(row["value"])


def _ensure_indexes(db):
    db.users.create_index([("id", ASCENDING)], unique=True)
    db.users.create_index([("email", ASCENDING)], unique=True)
    db.user_preferences.create_index([("user_id", ASCENDING)], unique=True)
    db.restaurants.create_index([("id", ASCENDING)], unique=True)
    db.restaurants.create_index([("name", TEXT), ("cuisine_type", TEXT), ("description", TEXT)])
    db.restaurants.create_index([("city", ASCENDING)])
    db.reviews.create_index([("id", ASCENDING)], unique=True)
    db.reviews.create_index([("restaurant_id", ASCENDING), ("created_at", ASCENDING)])
    db.reviews.create_index([("user_id", ASCENDING), ("restaurant_id", ASCENDING)], unique=True)
    db.favorites.create_index([("user_id", ASCENDING), ("restaurant_id", ASCENDING)], unique=True)
    db.sessions.create_index([("session_id", ASCENDING)], unique=True)
    db.sessions.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0)
    db.activity_logs.create_index([("created_at", ASCENDING)])
