from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.middleware.rate_limit import limiter
from app.schemas.auth import LoginRequest, RefreshRequest
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserRead
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register(request: Request, user_in: UserCreate, db: AsyncSession = Depends(get_db)) -> UserRead:
    """Create a new account."""
    return await AuthService(db).register(user_in)


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
async def login(request: Request, credentials: LoginRequest, db: AsyncSession = Depends(get_db)) -> Token:
    """Exchange email + password for an access/refresh token pair."""
    service = AuthService(db)
    user = await service.authenticate(credentials.email, credentials.password)
    return await service.issue_tokens(user)


@router.post("/refresh", response_model=Token)
@limiter.limit("20/minute")
async def refresh(request: Request, body: RefreshRequest, db: AsyncSession = Depends(get_db)) -> Token:
    """Exchange a valid, unexpired refresh token for a new token pair (rotates the refresh token)."""
    return await AuthService(db).refresh_tokens(body.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: RefreshRequest, db: AsyncSession = Depends(get_db)) -> None:
    """Revoke a refresh token, ending that session."""
    await AuthService(db).logout(body.refresh_token)
