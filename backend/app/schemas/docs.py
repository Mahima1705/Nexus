import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.documentation_history import DocumentationType


class DocumentationGenerateRequest(BaseModel):
    doc_type: DocumentationType


class DocumentationHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repository_id: uuid.UUID
    doc_type: DocumentationType
    content: str
    created_at: datetime
