"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.middleware.rate_limit import limiter, rate_limit_exceeded_handler

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("Starting %s v%s in %s mode", settings.PROJECT_NAME, settings.VERSION, settings.ENVIRONMENT)
    yield
    logger.info("Shutting down %s", settings.PROJECT_NAME)


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="AI-Powered Codebase Assistant — chat with, search, review, and document your repositories using RAG.",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Deliberately no SlowAPIMiddleware: it's BaseHTTPMiddleware-based, and that
    # combined with CORSMiddleware has a known Starlette interaction where an
    # unhandled exception gets double-processed (the client sees a broken/reset
    # connection instead of the clean JSON error our own handler already sent) —
    # reproduced during Milestone 11's browser testing. Rate limiting itself
    # still works: the @limiter.limit(...) decorators on individual endpoints
    # enforce and raise RateLimitExceeded on their own; the middleware only adds
    # X-RateLimit-* response headers, which aren't required for the limit to apply.
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    register_exception_handlers(app)

    app.include_router(api_router, prefix=settings.API_V1_STR)

    @app.get("/health", tags=["health"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok", "service": settings.PROJECT_NAME, "version": settings.VERSION}

    @app.get("/", tags=["health"])
    async def root() -> dict[str, str]:
        return {
            "message": f"{settings.PROJECT_NAME} API is running.",
            "docs": f"{settings.API_V1_STR}/docs",
        }

    return app


app = create_application()
