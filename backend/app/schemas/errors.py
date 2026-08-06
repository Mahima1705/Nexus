import uuid

from pydantic import BaseModel, Field


class ErrorAnalysisRequest(BaseModel):
    error_text: str = Field(min_length=1, max_length=20_000)
    repository_id: uuid.UUID | None = None


class ErrorAnalysisResponse(BaseModel):
    explanation: str
    likely_cause: str
    relevant_files: list[str]
    debugging_suggestions: list[str]
    possible_fixes: list[str]
