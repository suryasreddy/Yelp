"""
Migrate Lab 1 MySQL data into Lab 2 MongoDB collections.

Usage:
  python migrate_mysql_to_mongo.py
  python migrate_mysql_to_mongo.py --reset

Environment:
  DATABASE_URL -> MySQL source (existing Lab 1)
  MONGODB_URL / MONGODB_DB -> Mongo destination (Lab 2)
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from sqlalchemy.orm import Session, sessionmaker

import models
from database import engine, get_mongo_db


def now_utc():
    return datetime.now(timezone.utc)


def reset_mongo(db):
    for name in [
        "users",
        "user_preferences",
        "restaurants",
        "reviews",
        "favorites",
        "sessions",
        "activity_logs",
        "counters",
    ]:
        db[name].delete_many({})


def migrate_users(sql_db: Session, mongo_db):
    rows = sql_db.query(models.User).all()
    docs = []
    for row in rows:
        docs.append(
            {
                "id": row.id,
                "name": row.name,
                "email": row.email,
                "password_hash": row.password_hash,
                "role": row.role.value if hasattr(row.role, "value") else str(row.role),
                "phone": row.phone,
                "about_me": row.about_me,
                "city": row.city,
                "country": row.country,
                "state": row.state,
                "languages": row.languages,
                "gender": row.gender,
                "profile_picture": row.profile_picture,
                "restaurant_location": row.restaurant_location,
                "created_at": row.created_at or now_utc(),
                "updated_at": row.updated_at,
            }
        )
    if docs:
        mongo_db.users.insert_many(docs)
    return len(docs)


def migrate_preferences(sql_db: Session, mongo_db):
    rows = sql_db.query(models.UserPreferences).all()
    docs = []
    for row in rows:
        docs.append(
            {
                "id": row.id,
                "user_id": row.user_id,
                "cuisine_preferences": row.cuisine_preferences or [],
                "price_range": row.price_range,
                "preferred_location": row.preferred_location,
                "search_radius": row.search_radius if row.search_radius is not None else 10,
                "dietary_needs": row.dietary_needs or [],
                "ambiance_preferences": row.ambiance_preferences or [],
                "sort_preference": row.sort_preference or "rating",
            }
        )
    if docs:
        mongo_db.user_preferences.insert_many(docs)
    return len(docs)


def migrate_restaurants(sql_db: Session, mongo_db):
    rows = sql_db.query(models.Restaurant).all()
    docs = []
    for row in rows:
        docs.append(
            {
                "id": row.id,
                "name": row.name,
                "cuisine_type": row.cuisine_type,
                "address": row.address,
                "city": row.city,
                "state": row.state,
                "zip_code": row.zip_code,
                "description": row.description,
                "phone": row.phone,
                "website": row.website,
                "hours": row.hours,
                "price_tier": row.price_tier.value if hasattr(row.price_tier, "value") and row.price_tier else row.price_tier,
                "amenities": row.amenities or [],
                "photos": row.photos or [],
                "average_rating": float(row.average_rating or 0.0),
                "review_count": int(row.review_count or 0),
                "is_claimed": bool(row.is_claimed),
                "claimed_by": row.claimed_by,
                "added_by": row.added_by,
                "keywords": row.keywords or [],
                "created_at": row.created_at or now_utc(),
                "updated_at": row.updated_at,
            }
        )
    if docs:
        mongo_db.restaurants.insert_many(docs)
    return len(docs)


def migrate_reviews(sql_db: Session, mongo_db):
    rows = sql_db.query(models.Review).all()
    docs = []
    for row in rows:
        docs.append(
            {
                "id": row.id,
                "user_id": row.user_id,
                "restaurant_id": row.restaurant_id,
                "rating": row.rating,
                "comment": row.comment,
                "photos": row.photos or [],
                "created_at": row.created_at or now_utc(),
                "updated_at": row.updated_at,
            }
        )
    if docs:
        mongo_db.reviews.insert_many(docs)
    return len(docs)


def migrate_favorites(sql_db: Session, mongo_db):
    rows = sql_db.query(models.Favorite).all()
    docs = []
    for row in rows:
        docs.append(
            {
                "id": row.id,
                "user_id": row.user_id,
                "restaurant_id": row.restaurant_id,
                "created_at": row.created_at or now_utc(),
            }
        )
    if docs:
        mongo_db.favorites.insert_many(docs)
    return len(docs)


def update_counters(sql_db: Session, mongo_db):
    max_user = sql_db.query(models.User.id).order_by(models.User.id.desc()).first()
    max_restaurant = sql_db.query(models.Restaurant.id).order_by(models.Restaurant.id.desc()).first()
    max_review = sql_db.query(models.Review.id).order_by(models.Review.id.desc()).first()
    max_pref = sql_db.query(models.UserPreferences.id).order_by(models.UserPreferences.id.desc()).first()
    max_fav = sql_db.query(models.Favorite.id).order_by(models.Favorite.id.desc()).first()

    mongo_db.counters.replace_one({"_id": "users"}, {"_id": "users", "value": int(max_user[0] if max_user else 0)}, upsert=True)
    mongo_db.counters.replace_one({"_id": "restaurants"}, {"_id": "restaurants", "value": int(max_restaurant[0] if max_restaurant else 0)}, upsert=True)
    mongo_db.counters.replace_one({"_id": "reviews"}, {"_id": "reviews", "value": int(max_review[0] if max_review else 0)}, upsert=True)
    mongo_db.counters.replace_one({"_id": "user_preferences"}, {"_id": "user_preferences", "value": int(max_pref[0] if max_pref else 0)}, upsert=True)
    mongo_db.counters.replace_one({"_id": "favorites"}, {"_id": "favorites", "value": int(max_fav[0] if max_fav else 0)}, upsert=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Clear destination Mongo collections before migrating")
    args = parser.parse_args()

    mongo_db = get_mongo_db()
    if args.reset:
        reset_mongo(mongo_db)

    sql_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)()
    try:
        counts = {
            "users": migrate_users(sql_session, mongo_db),
            "preferences": migrate_preferences(sql_session, mongo_db),
            "restaurants": migrate_restaurants(sql_session, mongo_db),
            "reviews": migrate_reviews(sql_session, mongo_db),
            "favorites": migrate_favorites(sql_session, mongo_db),
        }
        update_counters(sql_session, mongo_db)

        mongo_db.activity_logs.insert_one(
            {
                "type": "migration.mysql_to_mongo",
                "status": "completed",
                "counts": counts,
                "created_at": now_utc(),
            }
        )

        print("MySQL -> Mongo migration complete.")
        for key, value in counts.items():
            print(f"- {key}: {value}")
    finally:
        sql_session.close()


if __name__ == "__main__":
    main()
