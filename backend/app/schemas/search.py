from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)


class SearchResponse(BaseModel):
    relevant_files: list[dict]
    explanation: str
    reasoning: str
