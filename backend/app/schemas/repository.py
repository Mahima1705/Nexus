import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.repository import RepositorySourceType, RepositoryStatus


class RepositoryCreateFromGitHub(BaseModel):
    source_url: str = Field(..., description="https://github.com/<owner>/<repo>")
    name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=2000)


class RepositoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    description: str | None
    source_type: RepositorySourceType
    source_url: str | None
    default_branch: str | None
    status: RepositoryStatus
    status_message: str | None
    total_files: int
    total_chunks: int
    created_at: datetime
    updated_at: datetime
