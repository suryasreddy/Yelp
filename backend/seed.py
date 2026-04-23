"""Seed MongoDB with demo users and restaurants for Lab 2."""

from datetime import datetime, timezone
from database import get_mongo_db, get_next_id
from auth import get_password_hash
from seed_restaurants import RESTAURANTS


def now():
    return datetime.now(timezone.utc)


def main():
    db = get_mongo_db()
    if db.users.count_documents({}) > 0:
        print("Database already seeded. Skipping.")
        return

    user1_id = get_next_id(db, "users")
    user2_id = get_next_id(db, "users")
    owner_id = get_next_id(db, "users")
    db.users.insert_many(
        [
            {
                "id": user1_id,
                "name": "Alice Johnson",
                "email": "alice@example.com",
                "password_hash": get_password_hash("password123"),
                "role": "user",
                "city": "San Francisco",
                "state": "CA",
                "country": "United States",
                "about_me": "Food lover and amateur chef!",
                "created_at": now(),
            },
            {
                "id": user2_id,
                "name": "Bob Chen",
                "email": "bob@example.com",
                "password_hash": get_password_hash("password123"),
                "role": "user",
                "city": "San Francisco",
                "state": "CA",
                "country": "United States",
                "created_at": now(),
            },
            {
                "id": owner_id,
                "name": "Maria Rossi",
                "email": "owner@example.com",
                "password_hash": get_password_hash("password123"),
                "role": "owner",
                "restaurant_location": "123 Mission St, San Francisco, CA",
                "city": "San Francisco",
                "state": "CA",
                "created_at": now(),
            },
        ]
    )

    for uid in [user1_id, user2_id, owner_id]:
        db.user_preferences.insert_one(
            {
                "user_id": uid,
                "cuisine_preferences": ["Italian", "Mexican"],
                "price_range": "$$",
                "dietary_needs": [],
                "ambiance_preferences": ["Casual"],
                "sort_preference": "rating",
                "search_radius": 10,
            }
        )

    restaurant_docs = []
    for data in RESTAURANTS:
        rid = get_next_id(db, "restaurants")
        row = {
            "id": rid,
            **data,
            "photos": [],
            "average_rating": 0.0,
            "review_count": 0,
            "is_claimed": False,
            "claimed_by": None,
            "added_by": user1_id,
            "created_at": now(),
        }
        restaurant_docs.append(row)
    if restaurant_docs:
        restaurant_docs[0]["is_claimed"] = True
        restaurant_docs[0]["claimed_by"] = owner_id
    db.restaurants.insert_many(restaurant_docs)

    db.favorites.insert_one({"user_id": user1_id, "restaurant_id": restaurant_docs[2]["id"], "created_at": now()})
    db.favorites.insert_one({"user_id": user1_id, "restaurant_id": restaurant_docs[25]["id"], "created_at": now()})
    db.favorites.insert_one({"user_id": user2_id, "restaurant_id": restaurant_docs[0]["id"], "created_at": now()})

    print("Seeded MongoDB successfully.")
    print("User:  alice@example.com / password123")
    print("User:  bob@example.com / password123")
    print("Owner: owner@example.com / password123")


if __name__ == "__main__":
    main()
