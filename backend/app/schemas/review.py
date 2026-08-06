import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.review_history import ReviewInputType


class ReviewSnippetRequest(BaseModel):
    source_code: str = Field(min_length=1, max_length=50_000)
    language: str | None = Field(default=None, max_length=64)
    filename: str | None = Field(default=None, max_length=1024)


class ReviewHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repository_id: uuid.UUID | None
    input_type: ReviewInputType
    input_reference: str | None
    language: str | None
    review_result: dict
    created_at: datetime
