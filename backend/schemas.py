from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    user = "user"
    owner = "owner"


class PriceTier(str, Enum):
    one = "$"
    two = "$$"
    three = "$$$"
    four = "$$$$"


# ─── Auth ────────────────────────────────────────────────────────────────────

class UserSignup(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.user
    restaurant_location: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user: "UserOut"


# ─── User ─────────────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id: int
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

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    about_me: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    languages: Optional[str] = None
    gender: Optional[str] = None


# ─── Preferences ──────────────────────────────────────────────────────────────

class PreferencesCreate(BaseModel):
    cuisine_preferences: List[str] = []
    price_range: Optional[str] = None
    preferred_location: Optional[str] = None
    search_radius: Optional[int] = 10
    dietary_needs: List[str] = []
    ambiance_preferences: List[str] = []
    sort_preference: Optional[str] = "rating"


class PreferencesOut(PreferencesCreate):
    id: int
    user_id: int

    class Config:
        from_attributes = True


# ─── Restaurant ───────────────────────────────────────────────────────────────

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
    price_tier: Optional[PriceTier] = None
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
    price_tier: Optional[PriceTier] = None
    amenities: Optional[List[str]] = None
    keywords: Optional[List[str]] = None


class RestaurantOut(BaseModel):
    id: int
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
    photos: Optional[List[str]] = []
    average_rating: float = 0.0
    review_count: int = 0
    is_claimed: bool = False
    claimed_by: Optional[int] = None
    added_by: Optional[int] = None
    keywords: Optional[List[str]] = []
    created_at: Optional[datetime] = None
    is_favorite: Optional[bool] = False

    class Config:
        from_attributes = True


# ─── Review ───────────────────────────────────────────────────────────────────

class ReviewCreate(BaseModel):
    rating: int
    comment: Optional[str] = None

    @field_validator("rating")
    @classmethod
    def rating_range(cls, v):
        if not 1 <= v <= 5:
            raise ValueError("Rating must be between 1 and 5")
        return v


class ReviewUpdate(BaseModel):
    rating: Optional[int] = None
    comment: Optional[str] = None

    @field_validator("rating")
    @classmethod
    def rating_range(cls, v):
        if v is not None and not 1 <= v <= 5:
            raise ValueError("Rating must be between 1 and 5")
        return v


class ReviewOut(BaseModel):
    id: int
    user_id: int
    restaurant_id: int
    rating: int
    comment: Optional[str] = None
    photos: Optional[List[str]] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    user: Optional[UserOut] = None

    class Config:
        from_attributes = True


# ─── AI Chat (stub for lab partner) ──────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[ChatMessage]] = []


class ChatResponse(BaseModel):
    response: str
    recommendations: Optional[List[Any]] = []


Token.model_rebuild()
