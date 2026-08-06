import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.repository import Repository
    from app.models.user import User


class ReviewInputType(str, enum.Enum):
    SNIPPET = "snippet"
    FILE = "file"


class ReviewHistory(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "review_history"

    # Nullable: a review can be run on an ad-hoc pasted snippet with no repository context.
    repository_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=True, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    input_type: Mapped[ReviewInputType] = mapped_column(
        Enum(ReviewInputType, name="review_input_type"), nullable=False
    )
    input_reference: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # {"bugs": [...], "security_issues": [...], "code_smells": [...],
    #  "performance_suggestions": [...], "best_practices": [...]}
    review_result: Mapped[dict] = mapped_column(JSON, nullable=False)

    repository: Mapped["Repository | None"] = relationship(back_populates="review_history")
    user: Mapped["User"] = relationship(back_populates="review_history")

    def __repr__(self) -> str:
        return f"<ReviewHistory id={self.id} input_type={self.input_type}>"
