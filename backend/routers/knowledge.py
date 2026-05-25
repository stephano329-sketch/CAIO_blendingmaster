"""Knowledge (경험치 DB) CRUD endpoints."""
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.models import KnowledgeEntry

router = APIRouter()


class KnowledgeIn(BaseModel):
    case_id: str
    season: str
    blend_components: dict
    cfpp: float
    cp: float
    pp: float
    ai_draft_decision: str | None = None
    q1_decision: str
    q2_reasons: list[str] = Field(default_factory=list)
    q3_priorities: list[str] = Field(default_factory=list)
    q4_risks: list[str] = Field(default_factory=list)
    q5_memo: str = ""
    author: str = "junior"


class KnowledgeOut(KnowledgeIn):
    entry_id: str
    created_at: datetime


@router.get("/knowledge", response_model=list[KnowledgeOut], tags=["knowledge"])
def list_entries(
    decision: str | None = Query(default=None),
    season: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[KnowledgeOut]:
    q = db.query(KnowledgeEntry)
    if decision:
        q = q.filter(KnowledgeEntry.q1_decision == decision)
    if season:
        q = q.filter(KnowledgeEntry.season == season)
    rows = q.order_by(KnowledgeEntry.created_at.desc()).limit(limit).all()
    return [KnowledgeOut.model_validate(r, from_attributes=True) for r in rows]


@router.post("/knowledge", response_model=KnowledgeOut, tags=["knowledge"])
def create_entry(payload: KnowledgeIn, db: Session = Depends(get_db)) -> KnowledgeOut:
    entry = KnowledgeEntry(
        entry_id=f"KB-{datetime.utcnow().strftime('%y%m%d-%H%M%S')}-{uuid4().hex[:4]}",
        **payload.model_dump(),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return KnowledgeOut.model_validate(entry, from_attributes=True)
