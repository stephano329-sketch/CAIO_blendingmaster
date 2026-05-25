"""Interview support endpoints — feeds the 지식 추출 page with real case data."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.models import Case, KnowledgeEntry

router = APIRouter()


class InterviewCase(BaseModel):
    case_id: str
    season: str
    blend_components: dict[str, str]   # human-formatted as "%"
    cfpp: float
    cp: float
    pp: float
    ai_draft_decision: str             # from Case.decision (rule-based pre-label)


def _format_blend(raw: dict | None) -> dict[str, str]:
    """Convert 0~1 fractions to 'NN%' strings keyed by uppercase short code."""
    if not raw:
        return {}
    out: dict[str, str] = {}
    code_map = {"lgo": "LGO", "hgo": "HGO", "lco": "LCO", "kero": "Kero", "biodiesel": "Bio"}
    for k, v in raw.items():
        label = code_map.get(k, k.upper())
        try:
            pct = round(float(v) * 100)
            out[label] = f"{pct}%"
        except (TypeError, ValueError):
            out[label] = str(v)
    return out


def _case_to_response(c: Case) -> InterviewCase:
    km = c.key_metrics or {}
    cfpp_val = km.get("cfpp_measured")
    if cfpp_val is None:
        cfpp_val = km.get("cfpp", 0.0)
    return InterviewCase(
        case_id=c.case_id,
        season=c.season,
        blend_components=_format_blend(c.blend_components),
        cfpp=float(cfpp_val or 0.0),
        cp=float(km.get("cp", 0.0) or 0.0),
        pp=float(km.get("pp", 0.0) or 0.0),
        ai_draft_decision=c.decision or "caution",
    )


@router.get("/interview/next-case", response_model=InterviewCase, tags=["interview"])
def next_case(
    skip_done: bool = Query(default=True, description="Skip cases already interviewed"),
    db: Session = Depends(get_db),
) -> InterviewCase:
    """Pick a case for the next interview session.

    Strategy: prefer cases with no existing KnowledgeEntry; if all interviewed,
    fall back to the most recent case so the page remains functional.
    """
    if skip_done:
        done_ids = {ke.case_id for ke in db.query(KnowledgeEntry.case_id).all()}
        q = db.query(Case)
        if done_ids:
            q = q.filter(~Case.case_id.in_(done_ids))
        row = q.order_by(Case.case_id).first()
        if row is not None:
            return _case_to_response(row)

    # Fallback: any case
    row = db.query(Case).order_by(Case.case_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="No cases available")
    return _case_to_response(row)


@router.get("/interview/case/{case_id}", response_model=InterviewCase, tags=["interview"])
def get_case(case_id: str, db: Session = Depends(get_db)) -> InterviewCase:
    c = db.get(Case, case_id)
    if not c:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    return _case_to_response(c)
