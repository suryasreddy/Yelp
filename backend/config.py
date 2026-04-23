from typing import Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/yelp_db"
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "yelp_db"
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_CLIENT_ID: str = "yelp-backend"
    # Accept SECRET_KEY (local) or JWT_SECRET (k8s/secrets.example.yaml) for the same value.
    SECRET_KEY: str = Field(
        default="change-this-secret-key-in-production",
        validation_alias=AliasChoices("SECRET_KEY", "JWT_SECRET"),
    )
    ALGORITHM: str = Field(
        default="HS256",
        validation_alias=AliasChoices("ALGORITHM", "JWT_ALGORITHM"),
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=1440,
        validation_alias=AliasChoices("ACCESS_TOKEN_EXPIRE_MINUTES", "SESSION_EXPIRE_MINUTES"),
    )
    UPLOAD_DIR: str = "uploads"
    OPENAI_API_KEY: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None
    ENABLE_AI_ROUTE: bool = False
    # JMeter / lab only: if True, POST review does not reject duplicate user+restaurant (Lab 1 UX is one review each).
    ALLOW_DUPLICATE_REVIEW_SUBMITS: bool = False


settings = Settings()
