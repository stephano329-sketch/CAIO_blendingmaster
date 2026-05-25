"""Consult service: vector search -> LLM (or fallback) -> citations."""
from __future__ import annotations

from backend.engine.rag_retriever import get_retriever, RetrievedDoc
from backend.engine.llm_client import generate_answer
from backend.schemas.consult import (
    ConsultRequest,
    ConsultResponse,
    ConsultCitation,
)


def consult(req: ConsultRequest) -> ConsultResponse:
    retriever = get_retriever()

    filters = _build_filters(req)
    docs = retriever.retrieve(query=req.query, top_k=req.top_k, filters=filters)

    snippets = [_doc_to_snippet(d) for d in docs]
    answer = generate_answer(req.query, snippets)

    citations = [
        ConsultCitation(
            doc_id=d.doc_id,
            doc_type=d.doc_type,
            section_title=d.metadata.get("section_title")
            or (d.metadata.get("decision") if d.doc_type == "case" else None),
            similarity_score=round(d.similarity_score, 3),
            preview=_preview(d.text),
        )
        for d in docs
    ]

    return ConsultResponse(
        answer=answer.text,
        used_llm=answer.used_llm,
        model=answer.model,
        citations=citations,
        retrieved_count=len(docs),
    )


def _build_filters(req: ConsultRequest) -> dict | None:
    clauses = []
    if req.doc_type:
        clauses.append({"doc_type": req.doc_type})
    if req.case_id:
        clauses.append({"doc_id": req.case_id})
    if req.season:
        clauses.append({"season": req.season})

    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def _doc_to_snippet(d: RetrievedDoc) -> dict:
    return {
        "doc_id": d.doc_id,
        "doc_type": d.doc_type,
        "section_title": d.metadata.get("section_title"),
        "decision": d.metadata.get("decision"),
        "text": d.text,
    }


def _preview(text: str, max_len: int = 240) -> str:
    s = (text or "").strip().replace("\n", " ")
    return s if len(s) <= max_len else s[:max_len] + "…"
