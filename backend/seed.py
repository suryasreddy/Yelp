"""Seed MongoDB with demo users, restaurants, and random reviews for chatbot testing."""

import random
from datetime import datetime, timedelta, timezone
from database import get_mongo_db, get_next_id
from auth import get_password_hash
from seed_restaurants import RESTAURANTS


def now():
    return datetime.now(timezone.utc)


def random_past_date(days_back=365):
    return datetime.now(timezone.utc) - timedelta(days=random.randint(1, days_back))


REVIEW_TEMPLATES = {
    5: [
        "Absolutely incredible experience! The food was outstanding and the service was impeccable. Will definitely be back.",
        "Best meal I've had in years. Every dish was perfectly prepared and the staff was so attentive.",
        "A hidden gem! The flavors were complex and the ambiance was perfect for a date night.",
        "Top-notch from start to finish. The chef clearly has a passion for great food.",
        "Exceeded every expectation. Fresh ingredients, creative presentation, and friendly staff.",
        "Worth every penny. This place sets the gold standard for its cuisine type.",
        "Phenomenal! The portions were generous and every bite was bursting with flavor.",
        "I've been to many restaurants but this one stands out. Exceptional food and service.",
    ],
    4: [
        "Really enjoyed our meal here. The food was delicious and service was prompt. Minor wait for a table but worth it.",
        "Great spot overall. The mains were fantastic, dessert was a bit underwhelming but still solid.",
        "Very good experience. The atmosphere was lovely and the food was fresh and flavorful.",
        "Would recommend to friends. The pasta was excellent and the wine selection is impressive.",
        "Solid restaurant with consistent quality. Prices are fair for what you get.",
        "Good food and nice ambiance. Service could be a touch faster but overall a great visit.",
        "Tasty food and friendly staff. A reliable go-to for a nice dinner out.",
        "Pretty good! The entrees were well-seasoned and the cocktails were creative.",
    ],
    3: [
        "Decent food but nothing memorable. Probably wouldn't go out of my way to return.",
        "Average experience overall. The food was okay but service felt rushed.",
        "Mixed feelings — some dishes were great, others were a miss. Has potential though.",
        "Fine for the price. Nothing special but gets the job done if you're in the area.",
        "Mediocre. The food was edible but the wait times were frustrating.",
        "Had high expectations based on reviews but it was just okay. Maybe caught them on a bad night.",
        "Middle of the road. The appetizers were better than the mains.",
        "Not bad but not great. The location is convenient which helps.",
    ],
    2: [
        "Disappointing visit. The food arrived cold and the waiter was inattentive.",
        "Expected better. The flavors were bland and the portion sizes were tiny for the price.",
        "Wouldn't rush back. Long wait, underwhelming food, and the place felt understaffed.",
        "Below average experience. The ingredients didn't taste fresh and the service was slow.",
        "Not worth the hype. Overpriced for what you get and the quality has clearly slipped.",
        "Had one good dish but everything else was forgettable. Management needs to up their game.",
    ],
    1: [
        "Terrible experience. Waited 45 minutes for food that was cold and tasteless.",
        "Awful. The worst meal I've had in this city. Avoid at all costs.",
        "Rude staff, poor food quality, and an unclean dining area. Will not return.",
        "Complete waste of money. Everything from the service to the food was subpar.",
        "Shocking how bad this place is. The reviews must be fake — nothing matched expectations.",
    ],
}

SEED_USERS = [
    {"name": "Alice Johnson", "email": "alice@example.com", "city": "San Francisco", "about_me": "Food lover and amateur chef!", "role": "user"},
    {"name": "Bob Chen", "email": "bob@example.com", "city": "San Francisco", "role": "user"},
    {"name": "Maria Rossi", "email": "owner@example.com", "city": "San Francisco", "role": "owner", "restaurant_location": "123 Mission St, San Francisco, CA"},
    {"name": "Priya Patel", "email": "priya@example.com", "city": "Oakland", "about_me": "Foodie who loves exploring local spots.", "role": "user"},
    {"name": "James Lee", "email": "james@example.com", "city": "San Jose", "about_me": "BBQ enthusiast and craft beer nerd.", "role": "user"},
    {"name": "Sofia Martinez", "email": "sofia@example.com", "city": "Berkeley", "about_me": "Vegetarian food blogger.", "role": "user"},
    {"name": "Derek Williams", "email": "derek@example.com", "city": "San Francisco", "about_me": "Sushi and ramen obsessed.", "role": "user"},
    {"name": "Hannah Kim", "email": "hannah@example.com", "city": "Palo Alto", "about_me": "Always hunting for the best desserts.", "role": "user"},
]


def _rating_weights():
    # Skew toward positive ratings to reflect typical review distributions
    return [1, 2, 3, 4, 5], [0.05, 0.10, 0.20, 0.35, 0.30]


def _seed_reviews(db, restaurant_docs, user_ids):
    ratings_choices, weights = _rating_weights()
    review_docs = []

    for restaurant in restaurant_docs:
        rid = restaurant["id"]
        # Each restaurant gets reviews from a random subset of users (2-6 reviewers)
        num_reviewers = random.randint(2, min(6, len(user_ids)))
        reviewers = random.sample(user_ids, num_reviewers)

        for uid in reviewers:
            rating = random.choices(ratings_choices, weights=weights, k=1)[0]
            comment = random.choice(REVIEW_TEMPLATES[rating])
            created = random_past_date(365)
            review_id = get_next_id(db, "reviews")
            review_docs.append({
                "id": review_id,
                "restaurant_id": rid,
                "user_id": uid,
                "rating": rating,
                "comment": comment,
                "photos": [],
                "created_at": created,
                "updated_at": created,
            })

    if review_docs:
        db.reviews.insert_many(review_docs)

    # Recalculate average_rating and review_count for each restaurant
    for restaurant in restaurant_docs:
        rid = restaurant["id"]
        reviews = list(db.reviews.find({"restaurant_id": rid}))
        count = len(reviews)
        avg = round(sum(r["rating"] for r in reviews) / count, 2) if count else 0.0
        db.restaurants.update_one({"id": rid}, {"$set": {"average_rating": avg, "review_count": count}})

    return len(review_docs)


def main():
    db = get_mongo_db()
    if db.users.count_documents({}) > 0:
        print("Database already seeded. Skipping.")
        return

    user_ids = []
    user_docs = []
    owner_id = None

    for i, u in enumerate(SEED_USERS):
        uid = get_next_id(db, "users")
        user_ids.append(uid)
        doc = {
            "id": uid,
            "name": u["name"],
            "email": u["email"],
            "password_hash": get_password_hash("password123"),
            "role": u["role"],
            "city": u.get("city", "San Francisco"),
            "state": "CA",
            "country": "United States",
            "created_at": now(),
        }
        if "about_me" in u:
            doc["about_me"] = u["about_me"]
        if "restaurant_location" in u:
            doc["restaurant_location"] = u["restaurant_location"]
        user_docs.append(doc)
        if u["role"] == "owner":
            owner_id = uid

    user1_id, user2_id = user_ids[0], user_ids[1]
    db.users.insert_many(user_docs)

    for uid in user_ids:
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

    num_reviews = _seed_reviews(db, restaurant_docs, user_ids)

    print("Seeded MongoDB successfully.")
    print(f"  {len(RESTAURANTS)} restaurants with {num_reviews} random reviews")
    print("User:  alice@example.com / password123")
    print("User:  bob@example.com / password123")
    print("Owner: owner@example.com / password123")
    print("Additional users: priya@example.com, james@example.com, sofia@example.com, derek@example.com, hannah@example.com / password123")


if __name__ == "__main__":
    main()
