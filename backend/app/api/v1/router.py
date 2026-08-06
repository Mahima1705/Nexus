"""Aggregates all v1 endpoint routers into a single APIRouter."""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, chat, docs, errors, repositories, review, search, users

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(repositories.router, prefix="/repositories", tags=["repositories"])
# chat and search extend the /repositories/{id} and /sessions/{id} resources directly
# (their route paths already include those segments), rather than nesting under an
# extra /chat or /search prefix.
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(search.router, tags=["search"])
api_router.include_router(review.router, prefix="/review", tags=["review"])
api_router.include_router(errors.router, prefix="/errors", tags=["errors"])
api_router.include_router(docs.router, prefix="/docs", tags=["docs"])
