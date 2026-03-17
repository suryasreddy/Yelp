from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, Boolean,
    ForeignKey, Enum, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


class UserRole(str, enum.Enum):
    user = "user"
    owner = "owner"


class PriceTier(str, enum.Enum):
    one = "$"
    two = "$$"
    three = "$$$"
    four = "$$$$"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.user, nullable=False)
    phone = Column(String(30))
    about_me = Column(Text)
    city = Column(String(100))
    country = Column(String(100))
    state = Column(String(10))
    languages = Column(String(255))
    gender = Column(String(30))
    profile_picture = Column(String(500))
    restaurant_location = Column(String(255))  # for owners
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    preferences = relationship("UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="user", cascade="all, delete-orphan")
    favorites = relationship("Favorite", back_populates="user", cascade="all, delete-orphan")
    added_restaurants = relationship("Restaurant", back_populates="added_by_user", foreign_keys="Restaurant.added_by")


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    cuisine_preferences = Column(JSON, default=list)
    price_range = Column(String(10))
    preferred_location = Column(String(255))
    search_radius = Column(Integer, default=10)
    dietary_needs = Column(JSON, default=list)
    ambiance_preferences = Column(JSON, default=list)
    sort_preference = Column(String(50), default="rating")

    user = relationship("User", back_populates="preferences")


class Restaurant(Base):
    __tablename__ = "restaurants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    cuisine_type = Column(String(100), index=True)
    address = Column(String(500))
    city = Column(String(100), index=True)
    state = Column(String(10))
    zip_code = Column(String(20))
    description = Column(Text)
    phone = Column(String(30))
    website = Column(String(500))
    hours = Column(JSON)
    price_tier = Column(Enum(PriceTier))
    amenities = Column(JSON, default=list)
    photos = Column(JSON, default=list)
    average_rating = Column(Float, default=0.0)
    review_count = Column(Integer, default=0)
    is_claimed = Column(Boolean, default=False)
    claimed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    added_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    keywords = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    reviews = relationship("Review", back_populates="restaurant", cascade="all, delete-orphan")
    favorites = relationship("Favorite", back_populates="restaurant", cascade="all, delete-orphan")
    added_by_user = relationship("User", back_populates="added_restaurants", foreign_keys=[added_by])
    owner = relationship("User", foreign_keys=[claimed_by])


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text)
    photos = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="reviews")
    restaurant = relationship("Restaurant", back_populates="reviews")


class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="favorites")
    restaurant = relationship("Restaurant", back_populates="favorites")
