"""Consult service: vector search + veteran knowledge -> LLM -> citations."""
from __future__ import annotations

from backend.db.database import SessionLocal
from backend.engine.rag_retriever import get_retriever, RetrievedDoc
from backend.engine.llm_client import generate_answer
from backend.models import KnowledgeEntry
from backend.schemas.consult import (
    ConsultRequest,
    ConsultResponse,
    ConsultCitation,
)

# Q-code → Korean label mapping for KB snippet rendering
_Q2_LABEL = {
    "metric_level": "검사값 절대 수준",
    "blend_component": "블렌딩 구성",
    "tank_history": "탱크 이력",
    "seasonality": "계절 영향",
    "additive": "첨가제 영향",
    "other": "기타",
}
_Q3_LABEL = {
    "retest": "검사 재확인",
    "tank_history": "탱크 이력",
    "blend_ratio": "블렌딩 비율",
    "additive_dose": "첨가제 투입량",
    "process_condition": "공정 조건",
}
_Q4_LABEL = {
    "within_spec": "기준내 안착 가능",
    "historical": "이력 영향",
    "post_issue": "출하 후 문제",
    "conditional": "조건부 품질 안착",
}
_DECISION_LABEL = {"normal": "정상", "caution": "주의", "risk": "위험"}
_SEASON_LABEL = {"winter": "동절기", "deep_winter": "혹한기"}
_AUTHOR_LABEL = {"junior": "김 연구원", "veteran": "이 부장"}

_MAX_KB_SNIPPETS = 15  # cap to keep prompt size sane


def consult(req: ConsultRequest) -> ConsultResponse:
    retriever = get_retriever()

    filters = _build_filters(req)
    docs = retriever.retrieve(query=req.query, top_k=req.top_k, filters=filters)
    doc_snippets = [_doc_to_snippet(d) for d in docs]

    kb_entries = _retrieve_knowledge(season=req.season)
    kb_snippets = [_kb_to_snippet(e) for e in kb_entries]

    snippets = doc_snippets + kb_snippets
    answer = generate_answer(req.query, snippets)

    citations: list[ConsultCitation] = [
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
    citations.extend(
        ConsultCitation(
            doc_id=f"KB-{e.entry_id[-4:]}" if len(e.entry_id) >= 4 else f"KB-{e.entry_id}",
            doc_type="knowledge",
            section_title=f"{_DECISION_LABEL.get(e.q1_decision, e.q1_decision)} · {_AUTHOR_LABEL.get(e.author, e.author)}",
            similarity_score=0.0,  # KB는 vector score 없음 — 별도 표시
            preview=_preview(e.q5_memo or "(메모 없음)"),
        )
        for e in kb_entries
    )

    return ConsultResponse(
        answer=answer.text,
        used_llm=answer.used_llm,
        model=answer.model,
        citations=citations,
        retrieved_count=len(docs) + len(kb_entries),
    )


def _retrieve_knowledge(season: str | None = None) -> list[KnowledgeEntry]:
    """Pull veteran knowledge entries from SQLite.

    Lightweight retrieval: filter by season if provided, return most recent first
    up to _MAX_KB_SNIPPETS entries. LLM decides which ones are relevant.
    """
    db = SessionLocal()
    try:
        q = db.query(KnowledgeEntry)
        if season:
            q = q.filter(KnowledgeEntry.season == season)
        return q.order_by(KnowledgeEntry.created_at.desc()).limit(_MAX_KB_SNIPPETS).all()
    finally:
        db.close()


def _kb_to_snippet(e: KnowledgeEntry) -> dict:
    """Render a knowledge entry as an LLM-readable snippet."""
    short_id = f"KB-{e.entry_id[-4:]}" if len(e.entry_id) >= 4 else f"KB-{e.entry_id}"
    season = _SEASON_LABEL.get(e.season, e.season)
    decision = _DECISION_LABEL.get(e.q1_decision, e.q1_decision)
    blend = ", ".join(f"{k} {v}" for k, v in (e.blend_components or {}).items())
    q2 = " / ".join(_Q2_LABEL.get(x, x) for x in (e.q2_reasons or []))
    q3 = " / ".join(_Q3_LABEL.get(x, x) for x in (e.q3_priorities or []))
    q4 = " / ".join(_Q4_LABEL.get(x, x) for x in (e.q4_risks or []))

    body_lines = [
        f"베테랑 판단 사례 ({_AUTHOR_LABEL.get(e.author, e.author)}, {season}, 원본 case={e.case_id})",
        f"- 블렌딩: {blend or '미기재'}",
        f"- 성상: CFPP {e.cfpp:.1f}°C / CP {e.cp:.1f}°C / PP {e.pp:.1f}°C",
        f"- Q1 판단: {decision}",
        f"- Q2 근거: {q2 or '없음'}",
        f"- Q3 확인 우선순위: {q3 or '없음'}",
        f"- Q4 리스크: {q4 or '없음'}",
        f"- Q5 메모: {e.q5_memo or '(없음)'}",
    ]
    return {
        "doc_id": short_id,
        "doc_type": "knowledge",
        "section_title": f"베테랑 {_DECISION_LABEL.get(e.q1_decision, e.q1_decision)} 판단",
        "decision": e.q1_decision,
        "text": "\n".join(body_lines),
    }


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
