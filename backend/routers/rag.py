"""RAG document inspection endpoints."""
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel

from backend.engine.rag_retriever import get_retriever

router = APIRouter()


class RagDoc(BaseModel):
    doc_id: str
    doc_type: str
    text: str
    metadata: dict[str, Any]


class RagListResponse(BaseModel):
    total: int
    items: list[RagDoc]


class RagSearchHit(RagDoc):
    similarity_score: float
    distance: float


class RagSearchResponse(BaseModel):
    query: str
    hits: list[RagSearchHit]


def _coll():
    return get_retriever()._collection  # internal access; intentional for inspection


@router.get("/rag/docs", response_model=RagListResponse, tags=["rag"])
def list_docs(
    doc_type: str | None = Query(default=None, description="Filter by doc_type (case, rule, doc, ...)"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> RagListResponse:
    """Paginated listing of RAG documents in the primary ChromaDB collection."""
    coll = _coll()
    where = {"doc_type": doc_type} if doc_type else None
    total = coll.count() if not where else len(coll.get(where=where, include=[])["ids"])
    raw = coll.get(where=where, limit=limit, offset=offset, include=["documents", "metadatas"])

    items: list[RagDoc] = []
    ids = raw.get("ids", []) or []
    docs = raw.get("documents", []) or []
    metas = raw.get("metadatas", []) or []
    for _id, text, meta in zip(ids, docs, metas):
        meta = meta or {}
        items.append(
            RagDoc(
                doc_id=meta.get("doc_id", _id),
                doc_type=meta.get("doc_type", "unknown"),
                text=text or "",
                metadata=meta,
            )
        )
    return RagListResponse(total=total, items=items)


@router.get("/rag/types", tags=["rag"])
def list_doc_types() -> dict[str, int]:
    """Counts per doc_type for filter UI."""
    coll = _coll()
    raw = coll.get(include=["metadatas"])
    counts: dict[str, int] = {}
    for meta in raw.get("metadatas", []) or []:
        t = (meta or {}).get("doc_type", "unknown")
        counts[t] = counts.get(t, 0) + 1
    return counts


@router.get("/rag/search", response_model=RagSearchResponse, tags=["rag"])
def search(
    q: str = Query(..., min_length=1),
    top_k: int = Query(default=5, ge=1, le=20),
    doc_type: str | None = Query(default=None),
) -> RagSearchResponse:
    """Vector similarity search across the RAG collection."""
    retriever = get_retriever()
    filters = {"doc_type": doc_type} if doc_type else None
    results = retriever.retrieve(query=q, top_k=top_k, filters=filters)
    hits = [
        RagSearchHit(
            doc_id=r.doc_id,
            doc_type=r.doc_type,
            text=r.text,
            metadata=r.metadata,
            similarity_score=round(r.similarity_score, 3),
            distance=round(r.distance, 3),
        )
        for r in results
    ]
    return RagSearchResponse(query=q, hits=hits)
