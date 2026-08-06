"""Imports every model so Base.metadata is fully populated for Alembic autogenerate.

This module is intentionally side-effect-only: Alembic's env.py imports `Base`
from here (not from base_class directly) to guarantee all tables are registered.
"""
from app.db.base_class import Base  # noqa: F401

from app.models.user import User  # noqa: F401
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.repository import Repository  # noqa: F401
from app.models.repository_file import RepositoryFile  # noqa: F401
from app.models.chat_session import ChatSession  # noqa: F401
from app.models.message import Message  # noqa: F401
from app.models.embedding_metadata import EmbeddingMetadata  # noqa: F401
from app.models.documentation_history import DocumentationHistory  # noqa: F401
from app.models.review_history import ReviewHistory  # noqa: F401
