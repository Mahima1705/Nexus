"""Custom exception hierarchy and FastAPI exception handlers.

Every handled error in the API responds with a consistent JSON shape:
    {"error": {"code": "SOME_CODE", "message": "human readable message", "details": {...}}}
"""
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)


class NexusException(Exception):
    """Base class for all application-raised (as opposed to framework-raised) errors."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)


class BadRequestException(NexusException):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "BAD_REQUEST"


class ValidationException(NexusException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "VALIDATION_ERROR"


class UnauthorizedException(NexusException):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "UNAUTHORIZED"


class ForbiddenException(NexusException):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "FORBIDDEN"


class NotFoundException(NexusException):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "NOT_FOUND"


class ConflictException(NexusException):
    status_code = status.HTTP_409_CONFLICT
    error_code = "CONFLICT"


class RateLimitException(NexusException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_code = "RATE_LIMIT_EXCEEDED"


class ExternalServiceException(NexusException):
    """Raised when a downstream dependency (LLM provider, Qdrant, GitHub, ...) fails."""

    status_code = status.HTTP_502_BAD_GATEWAY
    error_code = "EXTERNAL_SERVICE_ERROR"


def _error_response(status_code: int, code: str, message: str, details: dict[str, Any] | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details or {}}},
    )


def _sanitize_validation_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pydantic embeds the raw exception object under error["ctx"]["error"] when a
    custom validator raises ValueError — stringify it so the response is JSON-safe.
    """
    sanitized = []
    for error in errors:
        error = dict(error)
        if isinstance(error.get("ctx"), dict):
            error["ctx"] = {k: str(v) for k, v in error["ctx"].items()}
        sanitized.append(error)
    return sanitized


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NexusException)
    async def nexus_exception_handler(request: Request, exc: NexusException) -> JSONResponse:
        logger.warning("Handled NexusException %s: %s", exc.error_code, exc.message, extra={"path": request.url.path})
        return _error_response(exc.status_code, exc.error_code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.info("Request validation failed on %s", request.url.path)
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "VALIDATION_ERROR",
            "Request validation failed.",
            {"errors": _sanitize_validation_errors(exc.errors())},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception on %s", request.url.path)
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_ERROR",
            "An unexpected error occurred.",
        )
