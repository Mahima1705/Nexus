import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.repository import Repository
    from app.models.user import User


class DocumentationType(str, enum.Enum):
    README = "readme"
    PROJECT_OVERVIEW = "project_overview"
    FOLDER_STRUCTURE = "folder_structure"
    API_SUMMARY = "api_summary"
    INSTALLATION_GUIDE = "installation_guide"
    ENV_VARIABLES = "env_variables"
    FULL = "full"


class DocumentationHistory(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "documentation_history"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    doc_type: Mapped[DocumentationType] = mapped_column(
        Enum(DocumentationType, name="documentation_type"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    repository: Mapped["Repository"] = relationship(back_populates="documentation_history")
    user: Mapped["User"] = relationship(back_populates="documentation_history")

    def __repr__(self) -> str:
        return f"<DocumentationHistory id={self.id} doc_type={self.doc_type}>"
