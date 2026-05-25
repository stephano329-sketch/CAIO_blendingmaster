from typing import Literal
from pydantic import BaseModel, Field

DocType = Literal["process", "production", "feedstock", "case", "tacit"]


class ConsultRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    case_id: str | None = None
    season: str | None = None
    doc_type: DocType | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class ConsultCitation(BaseModel):
    doc_id: str
    doc_type: str
    section_title: str | None = None
    similarity_score: float
    preview: str


class ConsultResponse(BaseModel):
    answer: str
    used_llm: bool
    model: str | None = None
    citations: list[ConsultCitation]
    retrieved_count: int
