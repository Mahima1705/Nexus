"""Shared FastAPI dependencies for the API layer."""
import uuid

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.token import TokenPayload
from app.services.auth_service import AuthService

__all__ = ["get_db", "get_current_user", "get_current_active_superuser"]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_token(token)
        token_data = TokenPayload(**payload)
    except (JWTError, ValidationError):
        raise UnauthorizedException("Could not validate credentials.")

    if token_data.type != "access":
        raise UnauthorizedException("Provided token is not an access token.")

    try:
        user_id = uuid.UUID(token_data.sub)
    except ValueError:
        raise UnauthorizedException("Could not validate credentials.")

    user = await AuthService(db).get_user_by_id(user_id)
    if user is None:
        raise UnauthorizedException("User not found.")
    if not user.is_active:
        raise UnauthorizedException("This account is inactive.")
    return user


async def get_current_active_superuser(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_superuser:
        raise ForbiddenException("This action requires superuser privileges.")
    return current_user
