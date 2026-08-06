"""Application-wide logging configuration."""
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings


class JSONFormatter(logging.Formatter):
    """Renders log records as single-line JSON, convenient for log aggregators."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


class TextFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


_CONFIGURED = False


def configure_logging() -> None:
    """Idempotently configure the root logger. Safe to call multiple times."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)

    # Remove any pre-existing handlers (e.g. from uvicorn's default config)
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(JSONFormatter() if settings.LOG_JSON else TextFormatter())
    root_logger.addHandler(stream_handler)

    # Tame noisy third-party loggers without silencing our own
    for noisy_logger in ("httpx", "httpcore", "urllib3", "python_multipart"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
