import enum
import uuid
from typing import TYPE_CHECKING, List

from sqlalchemy import Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.chat_session import ChatSession
    from app.models.documentation_history import DocumentationHistory
    from app.models.embedding_metadata import EmbeddingMetadata
    from app.models.repository_file import RepositoryFile
    from app.models.review_history import ReviewHistory
    from app.models.user import User


class RepositorySourceType(str, enum.Enum):
    GITHUB = "github"
    ZIP = "zip"


class RepositoryStatus(str, enum.Enum):
    PENDING = "pending"
    CLONING = "cloning"
    EXTRACTING = "extracting"
    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"


class Repository(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "repositories"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[RepositorySourceType] = mapped_column(
        Enum(RepositorySourceType, name="repository_source_type"), nullable=False
    )
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    default_branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[RepositoryStatus] = mapped_column(
        Enum(RepositoryStatus, name="repository_status"),
        default=RepositoryStatus.PENDING,
        nullable=False,
    )
    status_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    qdrant_collection_name: Mapped[str] = mapped_column(String(255), nullable=False)
    total_files: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_chunks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    owner: Mapped["User"] = relationship(back_populates="repositories")
    files: Mapped[List["RepositoryFile"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )
    chat_sessions: Mapped[List["ChatSession"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )
    embedding_metadata: Mapped[List["EmbeddingMetadata"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )
    documentation_history: Mapped[List["DocumentationHistory"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )
    review_history: Mapped[List["ReviewHistory"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Repository id={self.id} name={self.name!r} status={self.status}>"
