"""Password hashing and JWT creation/verification primitives."""
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def _create_token(subject: str, token_type: Literal["access", "refresh"], expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    payload = {
        "sub": subject,
        "type": token_type,
        # Encoded as integers (standard JWT NumericDate) rather than datetime objects
        # to avoid any ambiguity in how the JWT library serializes them.
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        # Guarantees token uniqueness even when issued for the same subject within
        # the same second (iat/exp alone would otherwise collide and produce two
        # byte-identical tokens, breaking the refresh_tokens.token_hash uniqueness).
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(subject: str) -> str:
    return _create_token(subject, "access", timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))


def create_refresh_token(subject: str) -> str:
    return _create_token(subject, "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))


def decode_token(token: str) -> dict[str, Any]:
    """Decodes and verifies signature + expiry. Raises jose.JWTError on any failure."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def hash_token(token: str) -> str:
    """SHA-256 digest used to store/look up refresh tokens without persisting the raw secret."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
