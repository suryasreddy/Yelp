from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from database import engine, Base
import models  # noqa — ensures models are registered
from routers import auth, users, restaurants, owner, ai_assistant
from config import settings

# Create DB tables
Base.metadata.create_all(bind=engine)

# Create upload directories
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(f"{settings.UPLOAD_DIR}/profile", exist_ok=True)
os.makedirs(f"{settings.UPLOAD_DIR}/restaurants", exist_ok=True)
os.makedirs(f"{settings.UPLOAD_DIR}/reviews", exist_ok=True)

app = FastAPI(
    title="Yelp Prototype API",
    description="A Yelp-style restaurant discovery and review platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded files
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(restaurants.router)
app.include_router(owner.router)
app.include_router(ai_assistant.router)


@app.get("/")
def root():
    return {"message": "Yelp Prototype API is running", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}
