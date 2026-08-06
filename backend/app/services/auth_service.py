"""Business logic for registration, login, and JWT refresh-token lifecycle."""
import uuid
from datetime import datetime, timezone

from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, UnauthorizedException
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    hash_token,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import UserCreate

logger = get_logger(__name__)


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_user_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def register(self, user_in: UserCreate) -> User:
        if await self.get_user_by_email(user_in.email) is not None:
            raise ConflictException("A user with this email already exists.")

        user = User(
            email=user_in.email,
            hashed_password=get_password_hash(user_in.password),
            full_name=user_in.full_name,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        logger.info("Registered new user %s", user.id)
        return user

    async def authenticate(self, email: str, password: str) -> User:
        user = await self.get_user_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise UnauthorizedException("Incorrect email or password.")
        if not user.is_active:
            raise UnauthorizedException("This account is inactive.")
        return user

    async def issue_tokens(self, user: User) -> Token:
        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))

        payload = decode_token(refresh_token)
        expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)

        self.db.add(
            RefreshToken(
                user_id=user.id,
                token_hash=hash_token(refresh_token),
                expires_at=expires_at,
            )
        )
        await self.db.commit()

        return Token(access_token=access_token, refresh_token=refresh_token)

    async def refresh_tokens(self, refresh_token: str) -> Token:
        try:
            payload = decode_token(refresh_token)
        except JWTError:
            raise UnauthorizedException("Invalid or expired refresh token.")

        if payload.get("type") != "refresh":
            raise UnauthorizedException("Provided token is not a refresh token.")

        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token))
        )
        stored = result.scalar_one_or_none()
        if stored is None or stored.revoked:
            raise UnauthorizedException("Refresh token has been revoked or does not exist.")
        # SQLite (used in tests) doesn't round-trip tzinfo on DateTime(timezone=True)
        # columns the way Postgres does, so normalize before comparing.
        expires_at = stored.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise UnauthorizedException("Refresh token has expired.")

        user = await self.get_user_by_id(stored.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedException("User account is no longer active.")

        # Rotate on every use: the presented refresh token is single-use.
        stored.revoked = True
        await self.db.commit()

        return await self.issue_tokens(user)

    async def logout(self, refresh_token: str) -> None:
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token))
        )
        stored = result.scalar_one_or_none()
        if stored is not None:
            stored.revoked = True
            await self.db.commit()
