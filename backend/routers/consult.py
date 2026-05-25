from fastapi import APIRouter

from backend.schemas.consult import ConsultRequest, ConsultResponse
from backend.services.consult_service import consult as consult_service

router = APIRouter()


@router.post("/consult", response_model=ConsultResponse, tags=["consult"])
def consult(req: ConsultRequest) -> ConsultResponse:
    """RAG-based natural-language consultation.

    Retrieves the top-K relevant chunks from the primary RAG (docs + cases),
    then generates an answer with Claude (if ANTHROPIC_API_KEY is set) or a
    citation-only fallback summary.
    """
    return consult_service(req)
