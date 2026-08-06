import uuid
from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.embedding_metadata import EmbeddingMetadata
    from app.models.repository import Repository


class RepositoryFile(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "repository_files"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    language: Mapped[str | None] = mapped_column(String(64), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    is_indexed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    repository: Mapped["Repository"] = relationship(back_populates="files")
    embedding_metadata: Mapped[List["EmbeddingMetadata"]] = relationship(
        back_populates="file", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<RepositoryFile id={self.id} file_path={self.file_path!r}>"
