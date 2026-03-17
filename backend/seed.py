"""
Run this after the FastAPI server has started to seed the database with sample data.
Usage: python seed.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from database import SessionLocal, engine, Base
import models
from auth import get_password_hash

Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    # Check already seeded
    if db.query(models.User).count() > 0:
        print("Database already seeded. Skipping.")
        sys.exit(0)

    # Users
    user1 = models.User(name="Alice Johnson", email="alice@example.com", password_hash=get_password_hash("password123"), role=models.UserRole.user, city="San Francisco", state="CA", country="United States", about_me="Food lover and amateur chef!")
    user2 = models.User(name="Bob Chen", email="bob@example.com", password_hash=get_password_hash("password123"), role=models.UserRole.user, city="San Francisco", state="CA", country="United States")
    owner1 = models.User(name="Maria Rossi", email="owner@example.com", password_hash=get_password_hash("password123"), role=models.UserRole.owner, restaurant_location="123 Mission St, San Francisco, CA", city="San Francisco", state="CA")

    db.add_all([user1, user2, owner1])
    db.flush()

    # Preferences
    for u in [user1, user2, owner1]:
        db.add(models.UserPreferences(user_id=u.id, cuisine_preferences=["Italian","Mexican"], price_range="$$", dietary_needs=[], ambiance_preferences=["Casual"], sort_preference="rating"))

    # Restaurants
    restaurants_data = [
        dict(name="Tony's Little Italy", cuisine_type="Italian", address="1800 Washington St", city="San Francisco", state="CA", zip_code="94109", description="Authentic Italian cuisine with homemade pasta and a cozy atmosphere. Family-owned since 1987.", phone="(415) 555-0101", price_tier=models.PriceTier.two, amenities=["WiFi","Reservations","Family-friendly"], keywords=["pasta","pizza","romantic"], hours={"Monday":"11am-10pm","Tuesday":"11am-10pm","Wednesday":"11am-10pm","Thursday":"11am-10pm","Friday":"11am-11pm","Saturday":"10am-11pm","Sunday":"10am-9pm"}),
        dict(name="Dragon Palace", cuisine_type="Chinese", address="640 Jackson St", city="San Francisco", state="CA", zip_code="94133", description="Traditional Cantonese dim sum and seafood. A Chinatown institution for over 30 years.", phone="(415) 555-0202", price_tier=models.PriceTier.two, amenities=["Takeout","Family-friendly","Parking"], keywords=["dim sum","seafood","family"], hours={"Monday":"9am-9pm","Tuesday":"9am-9pm","Wednesday":"9am-9pm","Thursday":"9am-9pm","Friday":"9am-10pm","Saturday":"8am-10pm","Sunday":"8am-9pm"}),
        dict(name="Sakura Sushi", cuisine_type="Japanese", address="2001 Union St", city="San Francisco", state="CA", zip_code="94123", description="Premium omakase and à la carte sushi. Fresh fish flown in daily from Japan.", phone="(415) 555-0303", price_tier=models.PriceTier.three, amenities=["Reservations","Bar","WiFi"], keywords=["sushi","omakase","fresh fish","date night"], hours={"Tuesday":"5pm-10pm","Wednesday":"5pm-10pm","Thursday":"5pm-10pm","Friday":"5pm-11pm","Saturday":"5pm-11pm","Sunday":"5pm-9pm"}),
        dict(name="The Green Bowl", cuisine_type="Vegan", address="525 Hayes St", city="San Francisco", state="CA", zip_code="94102", description="100% plant-based café serving nourishing bowls, smoothies, and seasonal specials.", phone="(415) 555-0404", price_tier=models.PriceTier.two, amenities=["WiFi","Takeout","Delivery","Outdoor Seating"], keywords=["vegan","healthy","bowls","gluten-free"], hours={"Monday":"8am-8pm","Tuesday":"8am-8pm","Wednesday":"8am-8pm","Thursday":"8am-8pm","Friday":"8am-9pm","Saturday":"9am-9pm","Sunday":"9am-7pm"}),
        dict(name="El Farolito", cuisine_type="Mexican", address="2779 Mission St", city="San Francisco", state="CA", zip_code="94110", description="Late-night Mission District taqueria famous for its oversized burritos and street tacos.", phone="(415) 555-0505", price_tier=models.PriceTier.one, amenities=["Takeout","Family-friendly"], keywords=["tacos","burritos","late night","cheap eats"], hours={"Monday":"10am-2am","Tuesday":"10am-2am","Wednesday":"10am-2am","Thursday":"10am-2am","Friday":"10am-3am","Saturday":"10am-3am","Sunday":"10am-2am"}),
        dict(name="Fog City Diner", cuisine_type="American", address="1300 Battery St", city="San Francisco", state="CA", zip_code="94111", description="Classic American diner with a modern SF twist. Burgers, shakes, and all-day breakfast.", phone="(415) 555-0606", price_tier=models.PriceTier.two, amenities=["Bar","Family-friendly","Parking","WiFi"], keywords=["burgers","brunch","comfort food","diner"], hours={"Monday":"7am-10pm","Tuesday":"7am-10pm","Wednesday":"7am-10pm","Thursday":"7am-11pm","Friday":"7am-midnight","Saturday":"8am-midnight","Sunday":"8am-9pm"}),
        dict(name="Nopa", cuisine_type="American", address="560 Divisadero St", city="San Francisco", state="CA", zip_code="94117", description="Farm-to-table American fare in a stunning converted bank space. Award-winning cocktail program.", phone="(415) 555-0707", price_tier=models.PriceTier.three, amenities=["Bar","Reservations","WiFi","Outdoor Seating"], keywords=["farm-to-table","cocktails","upscale","date night"], hours={"Tuesday":"5pm-1am","Wednesday":"5pm-1am","Thursday":"5pm-1am","Friday":"5pm-1am","Saturday":"10am-2pm", "Sunday":"10am-2pm"}),
        dict(name="Tartine Bakery", cuisine_type="French", address="600 Guerrero St", city="San Francisco", state="CA", zip_code="94110", description="World-renowned artisan bakery. Come for the fresh-from-the-oven country bread at 5pm.", phone="(415) 555-0808", price_tier=models.PriceTier.two, amenities=["Takeout","WiFi"], keywords=["bakery","bread","pastries","coffee","brunch"], hours={"Monday":"Closed","Tuesday":"Closed","Wednesday":"8am-7pm","Thursday":"8am-7pm","Friday":"8am-8pm","Saturday":"8am-8pm","Sunday":"9am-3pm"}),
    ]

    restaurant_objs = []
    for i, data in enumerate(restaurants_data):
        r = models.Restaurant(**data, added_by=user1.id)
        db.add(r)
        restaurant_objs.append(r)

    db.flush()

    # Claim restaurant for owner
    restaurant_objs[0].is_claimed = True
    restaurant_objs[0].claimed_by = owner1.id

    # Reviews
    reviews = [
        (user1, 0, 5, "Absolutely the best Italian food in SF! The cacio e pepe is life-changing. Service was warm and attentive."),
        (user2, 0, 4, "Great authentic pasta, very cozy place. A bit loud on weekends but the food makes up for it."),
        (user1, 1, 4, "Excellent dim sum! Go early on weekends or you'll wait an hour. The har gow and pork buns are must-orders."),
        (user2, 1, 5, "Best dim sum in Chinatown, hands down. We go every Sunday."),
        (user1, 2, 5, "The omakase here is incredible. Chef Tanaka sources the most pristine fish. Worth every penny."),
        (user2, 3, 5, "As a vegan, I'm always skeptical but this place genuinely delivers. The jackfruit bowl is amazing!"),
        (user1, 3, 4, "Fresh, creative, and filling. Great spot for a healthy lunch."),
        (user2, 4, 5, "The best burrito I've had in my life and it only cost $12. Cash only so bring cash!"),
        (user1, 4, 4, "Authentic and cheap. The al pastor tacos are excellent."),
        (user1, 5, 4, "Classic American comfort food done right. The milkshakes are incredible."),
        (user2, 6, 5, "Stunning space, innovative menu, exceptional cocktails. One of SF's best."),
        (user1, 7, 5, "Worth the wait. The country bread is something special. Get there at 5pm sharp."),
        (user2, 7, 4, "Wonderful croissants and morning buns. The lines can be brutal but it's worth it."),
    ]

    for user, rest_idx, rating, comment in reviews:
        db.add(models.Review(user_id=user.id, restaurant_id=restaurant_objs[rest_idx].id, rating=rating, comment=comment))

    db.flush()

    # Recalculate ratings
    from sqlalchemy import func
    for r in restaurant_objs:
        result = db.query(func.avg(models.Review.rating), func.count(models.Review.id)).filter(models.Review.restaurant_id == r.id).first()
        r.average_rating = round(float(result[0] or 0), 2)
        r.review_count = result[1] or 0

    # Favorites
    db.add(models.Favorite(user_id=user1.id, restaurant_id=restaurant_objs[2].id))
    db.add(models.Favorite(user_id=user1.id, restaurant_id=restaurant_objs[6].id))
    db.add(models.Favorite(user_id=user2.id, restaurant_id=restaurant_objs[0].id))

    db.commit()
    print("✅ Database seeded successfully!")
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
