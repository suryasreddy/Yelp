import os


class Settings:
    MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://mongodb:27017")
    MONGODB_DB = os.getenv("MONGODB_DB", "yelp_lab2")
    JWT_SECRET = os.getenv("JWT_SECRET", "change-me-lab2")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    SESSION_EXPIRE_MINUTES = int(os.getenv("SESSION_EXPIRE_MINUTES", "1440"))
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    KAFKA_CLIENT_ID = os.getenv("KAFKA_CLIENT_ID", "yelp-lab2")


settings = Settings()
