"""
Seed the database with demo users and 50 varied restaurants.
Usage: python seed.py

Requires: MySQL running and .env configured.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import func

from database import SessionLocal, engine, Base
import models
from auth import get_password_hash
from seed_restaurants import RESTAURANTS

Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    if db.query(models.User).count() > 0:
        print("Database already seeded. Skipping.")
        print("To add the 50-restaurant set to an existing DB, run: python seed_restaurants.py")
        sys.exit(0)

    user1 = models.User(
        name="Alice Johnson",
        email="alice@example.com",
        password_hash=get_password_hash("password123"),
        role=models.UserRole.user,
        city="San Francisco",
        state="CA",
        country="United States",
        about_me="Food lover and amateur chef!",
    )
    user2 = models.User(
        name="Bob Chen",
        email="bob@example.com",
        password_hash=get_password_hash("password123"),
        role=models.UserRole.user,
        city="San Francisco",
        state="CA",
        country="United States",
    )
    owner1 = models.User(
        name="Maria Rossi",
        email="owner@example.com",
        password_hash=get_password_hash("password123"),
        role=models.UserRole.owner,
        restaurant_location="123 Mission St, San Francisco, CA",
        city="San Francisco",
        state="CA",
    )

    db.add_all([user1, user2, owner1])
    db.flush()

    for u in [user1, user2, owner1]:
        db.add(
            models.UserPreferences(
                user_id=u.id,
                cuisine_preferences=["Italian", "Mexican"],
                price_range="$$",
                dietary_needs=[],
                ambiance_preferences=["Casual"],
                sort_preference="rating",
            )
        )

    restaurant_objs = []
    for data in RESTAURANTS:
        r = models.Restaurant(**data, added_by=user1.id)
        db.add(r)
        restaurant_objs.append(r)

    db.flush()

    restaurant_objs[0].is_claimed = True
    restaurant_objs[0].claimed_by = owner1.id

    # Two short review templates per slot — rotate so every place has 1–2 reviews
    snippets = [
        "Really enjoyed our meal here. Would recommend.",
        "Great flavors and friendly staff.",
        "Solid choice in the neighborhood.",
        "Worth the price — we'll be back.",
        "Perfect for a casual night out.",
        "Impressive quality and atmosphere.",
    ]

    for i, r in enumerate(restaurant_objs):
        c1 = f"{snippets[i % len(snippets)]} {r.name} hits the spot."
        db.add(
            models.Review(
                user_id=user1.id,
                restaurant_id=r.id,
                rating=5 if i % 4 != 0 else 4,
                comment=c1,
            )
        )
        if i % 2 == 0:
            c2 = f"Second visit — still consistent. Love the {r.cuisine_type or 'food'} here."
            db.add(
                models.Review(
                    user_id=user2.id,
                    restaurant_id=r.id,
                    rating=4 if i % 3 != 0 else 5,
                    comment=c2,
                )
            )

    db.flush()

    for r in restaurant_objs:
        result = (
            db.query(func.avg(models.Review.rating), func.count(models.Review.id))
            .filter(models.Review.restaurant_id == r.id)
            .first()
        )
        r.average_rating = round(float(result[0] or 0), 2)
        r.review_count = result[1] or 0

    db.add(models.Favorite(user_id=user1.id, restaurant_id=restaurant_objs[2].id))
    db.add(models.Favorite(user_id=user1.id, restaurant_id=restaurant_objs[25].id))
    db.add(models.Favorite(user_id=user2.id, restaurant_id=restaurant_objs[0].id))

    db.commit()
    print("✅ Database seeded successfully!")
    print(f"   Loaded {len(RESTAURANTS)} restaurants across SF, Oakland, Berkeley, San Jose, Palo Alto.")
    print("\nSample accounts:")
    print("  User:  alice@example.com  / password123")
    print("  User:  bob@example.com    / password123")
    print("  Owner: owner@example.com  / password123")

except Exception as e:
    db.rollback()
    print(f"❌ Error seeding database: {e}")
    raise
finally:
    db.close()
