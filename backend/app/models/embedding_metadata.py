import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.repository import Repository
    from app.models.repository_file import RepositoryFile


class EmbeddingMetadata(UUIDMixin, TimestampMixin, Base):
    """Postgres-side mirror of a chunk stored in Qdrant.

    Qdrant holds the vector + the same metadata as payload for fast retrieval;
    this table lets us query/manage chunks relationally (e.g. delete all chunks
    for a file on re-index) without round-tripping through Qdrant.
    """

    __tablename__ = "embedding_metadata"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("repository_files.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Matches the point ID used in Qdrant for this exact chunk.
    qdrant_point_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    language: Mapped[str | None] = mapped_column(String(64), nullable=True)
    start_line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    repository: Mapped["Repository"] = relationship(back_populates="embedding_metadata")
    file: Mapped["RepositoryFile"] = relationship(back_populates="embedding_metadata")

    def __repr__(self) -> str:
        return f"<EmbeddingMetadata id={self.id} file_path={self.file_path!r} chunk_index={self.chunk_index}>"
