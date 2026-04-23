from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, EmailStr, field_validator


class UserSignup(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "user"
    restaurant_location: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_len(cls, value: str):
        if len(value) < 6:
            raise ValueError("Password must be at least 6 characters")
        return value


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    role: str
    phone: Optional[str] = None
    about_me: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    languages: Optional[str] = None
    gender: Optional[str] = None
    profile_picture: Optional[str] = None
    restaurant_location: Optional[str] = None
    created_at: Optional[datetime] = None


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut


class PreferencesCreate(BaseModel):
    cuisine_preferences: List[str] = []
    price_range: Optional[str] = None
    preferred_location: Optional[str] = None
    search_radius: Optional[int] = 10
    dietary_needs: List[str] = []
    ambiance_preferences: List[str] = []
    sort_preference: Optional[str] = "rating"


class RestaurantCreate(BaseModel):
    name: str
    cuisine_type: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    description: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    hours: Optional[Any] = None
    price_tier: Optional[str] = None
    amenities: Optional[List[str]] = []
    keywords: Optional[List[str]] = []


class RestaurantUpdate(BaseModel):
    name: Optional[str] = None
    cuisine_type: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    description: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    hours: Optional[Any] = None
    price_tier: Optional[str] = None
    amenities: Optional[List[str]] = None
    keywords: Optional[List[str]] = None


class ReviewCreate(BaseModel):
    rating: int
    comment: Optional[str] = None

    @field_validator("rating")
    @classmethod
    def rating_range(cls, value: int):
        if value < 1 or value > 5:
            raise ValueError("Rating must be between 1 and 5")
        return value


class ReviewUpdate(BaseModel):
    rating: Optional[int] = None
    comment: Optional[str] = None
