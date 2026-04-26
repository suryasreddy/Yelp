from datetime import timedelta
import secrets
from jose import jwt, JWTError
from passlib.context import CryptContext
from .config import settings
from .mongo import get_db, now_utc


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_session_token(user_id: str):
    db = get_db()
    created = now_utc()
    expires = created + timedelta(minutes=settings.SESSION_EXPIRE_MINUTES)
    session_id = secrets.token_urlsafe(24)
    db.sessions.insert_one(
        {
            "session_id": session_id,
            "user_id": user_id,
            "createdAt": created,
            "expiresAt": expires,
        }
    )
    token = jwt.encode(
        {"sub": user_id, "sid": session_id, "exp": expires},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    return token


def decode_token(token: str):
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


def validate_session_token(token: str):
    try:
        payload = decode_token(token)
    except JWTError:
        return None
    session_id = payload.get("sid")
    user_id = payload.get("sub")
    if not session_id or not user_id:
        return None
    db = get_db()
    session = db.sessions.find_one({"session_id": session_id, "user_id": user_id})
    if not session:
        return None
    return user_id
