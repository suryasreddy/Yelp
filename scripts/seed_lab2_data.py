import uuid
from services.shared.mongo import get_db, now_utc
from services.shared.security import hash_password


def seed():
    db = get_db()
    if db.users.count_documents({}) > 0:
        print("Lab2 MongoDB already seeded. Skipping.")
        return
    alice_id = str(uuid.uuid4())
    owner_id = str(uuid.uuid4())
    db.users.insert_many(
        [
            {
                "_id": alice_id,
                "name": "Alice Johnson",
                "email": "alice@example.com",
                "password_hash": hash_password("password123"),
                "role": "user",
                "city": "San Francisco",
                "state": "CA",
                "country": "United States",
                "created_at": now_utc(),
            },
            {
                "_id": owner_id,
                "name": "Owner Demo",
                "email": "owner@example.com",
                "password_hash": hash_password("password123"),
                "role": "owner",
                "restaurant_location": "San Francisco",
                "created_at": now_utc(),
            },
        ]
    )
    db.preferences.insert_many(
        [
            {"user_id": alice_id, "cuisine_preferences": ["Italian"], "price_range": "$$", "search_radius": 10, "dietary_needs": [], "ambiance_preferences": ["Casual"], "sort_preference": "rating"},
            {"user_id": owner_id, "cuisine_preferences": [], "price_range": "$$", "search_radius": 10, "dietary_needs": [], "ambiance_preferences": [], "sort_preference": "rating"},
        ]
    )
    r1 = str(uuid.uuid4())
    r2 = str(uuid.uuid4())
    db.restaurants.insert_many(
        [
            {
                "_id": r1,
                "name": "Golden Gate Pizza",
                "cuisine_type": "Italian",
                "address": "1 Market St",
                "city": "San Francisco",
                "state": "CA",
                "zip_code": "94105",
                "description": "Family friendly pizza spot",
                "price_tier": "$$",
                "amenities": ["wifi"],
                "photos": [],
                "average_rating": 0.0,
                "review_count": 0,
                "is_claimed": True,
                "claimed_by": owner_id,
                "added_by": owner_id,
                "created_at": now_utc(),
            },
            {
                "_id": r2,
                "name": "Bay Sushi House",
                "cuisine_type": "Japanese",
                "address": "20 Howard St",
                "city": "San Francisco",
                "state": "CA",
                "zip_code": "94105",
                "description": "Fresh omakase and rolls",
                "price_tier": "$$$",
                "amenities": ["reservations"],
                "photos": [],
                "average_rating": 0.0,
                "review_count": 0,
                "is_claimed": False,
                "claimed_by": None,
                "added_by": owner_id,
                "created_at": now_utc(),
            },
        ]
    )
    print("Seeded Lab2 MongoDB data.")
    print("User login: alice@example.com / password123")
    print("Owner login: owner@example.com / password123")


if __name__ == "__main__":
    seed()
