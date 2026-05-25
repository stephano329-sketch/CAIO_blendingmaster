from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.models import Case

router = APIRouter()


@router.get("/cases", tags=["cases"])
def list_cases(
    season: str | None = Query(default=None),
    decision: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(Case)
    if season:
        q = q.filter(Case.season == season)
    if decision:
        q = q.filter(Case.decision == decision)
    rows = q.limit(limit).all()
    return [
        {
            "case_id": r.case_id,
            "season": r.season,
            "decision": r.decision,
            "target_cfpp": r.target_cfpp,
            "rule_summary": r.rule_summary,
        }
        for r in rows
    ]


@router.get("/cases/{case_id}", tags=["cases"])
def get_case(case_id: str, db: Session = Depends(get_db)):
    c = db.get(Case, case_id)
    if not c:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    return {
        "case_id": c.case_id,
        "season": c.season,
        "tank_history_flag": c.tank_history_flag,
        "target_cfpp": c.target_cfpp,
        "decision": c.decision,
        "reason_codes": c.reason_codes,
        "check_priority": c.check_priority,
        "risk_codes": c.risk_codes,
        "rule_summary": c.rule_summary,
        "narrative": c.narrative,
        "blend_components": c.blend_components,
        "key_metrics": c.key_metrics,
        "actual_outcome": c.actual_outcome,
    }
