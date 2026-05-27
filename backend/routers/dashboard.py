"""Dashboard aggregate endpoints (stats + recent decision logs)."""
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.models import DecisionLog

router = APIRouter()

# Rough cost-saving estimate per accepted recommendation (KRW × 10000).
# Calibrated against an ops assumption: each AI-assisted batch saves ~26만원
# (WAFI over-injection avoidance + retest avoidance averaged).
SAVING_PER_BATCH_MAN_WON = 26


class DashboardStats(BaseModel):
    today_batch_count: int
    month_judge_count: int
    month_saving_man_won: int


class RecentLog(BaseModel):
    date: str           # YYYY-MM-DD
    log_id: str
    pred_cfpp: float
    wafi_suggested: float
    actual_cfpp: float | None
    actual_wafi: float | None
    decision: str
    selected_scenario: str | None


@router.get("/dashboard/stats", response_model=DashboardStats, tags=["dashboard"])
def stats(db: Session = Depends(get_db)) -> DashboardStats:
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    month_start = datetime(now.year, now.month, 1)

    today_count = (
        db.query(func.count(DecisionLog.log_id))
        .filter(DecisionLog.created_at >= today_start)
        .scalar()
        or 0
    )
    month_count = (
        db.query(func.count(DecisionLog.log_id))
        .filter(DecisionLog.created_at >= month_start)
        .scalar()
        or 0
    )

    return DashboardStats(
        today_batch_count=int(today_count),
        month_judge_count=int(month_count),
        month_saving_man_won=int(month_count) * SAVING_PER_BATCH_MAN_WON,
    )


@router.get("/dashboard/recent-logs", response_model=list[RecentLog], tags=["dashboard"])
def recent_logs(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> list[RecentLog]:
    rows = (
        db.query(DecisionLog)
        .order_by(DecisionLog.created_at.desc())
        .limit(limit)
        .all()
    )

    out: list[RecentLog] = []
    for r in rows:
        rec: dict[str, Any] = r.ai_recommendation or {}
        scenarios = rec.get("scenarios") or []
        selected_label = r.selected_scenario or "balanced"
        chosen = next((s for s in scenarios if s.get("label") == selected_label), None)
        actual = r.actual_outcome or {}

        out.append(
            RecentLog(
                date=r.created_at.strftime("%Y-%m-%d"),
                log_id=r.log_id,
                pred_cfpp=float((chosen or {}).get("predicted_cfpp", rec.get("predicted_cfpp_baseline", 0.0))),
                wafi_suggested=float((chosen or {}).get("wafi_ppm", 0.0)),
                actual_cfpp=actual.get("cfpp"),
                actual_wafi=actual.get("wafi_ppm"),
                decision=rec.get("decision", "normal"),
                selected_scenario=r.selected_scenario,
            )
        )
    return out


class BatchLog(BaseModel):
    log_id: str
    created_at: datetime
    season: str
    blend_components: dict[str, float]
    target_cfpp: float
    predicted_cfpp_baseline: float
    selected_scenario: str | None
    selected_wafi_ppm: float | None
    selected_wafi_type: str | None
    predicted_cfpp_after_wafi: float | None
    margin_to_target: float | None
    check_priority: list[str]
    similar_case_ids: list[str]
    actual_cfpp: float | None
    actual_wafi: float | None


@router.get("/journal/batches", response_model=list[BatchLog], tags=["dashboard"])
def list_batches(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[BatchLog]:
    """Full DecisionLog rows formatted for the 제품 배합 일지 page."""
    rows = (
        db.query(DecisionLog)
        .order_by(DecisionLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    out: list[BatchLog] = []
    for r in rows:
        inp = r.input or {}
        rec = r.ai_recommendation or {}
        actual = r.actual_outcome or {}
        scenarios = rec.get("scenarios") or []
        chosen = next((s for s in scenarios if s.get("label") == r.selected_scenario), None)
        out.append(
            BatchLog(
                log_id=r.log_id,
                created_at=r.created_at,
                season=inp.get("season", ""),
                blend_components=inp.get("blend_components") or {},
                target_cfpp=float(inp.get("target_cfpp", 0.0)),
                predicted_cfpp_baseline=float(rec.get("predicted_cfpp_baseline", 0.0)),
                selected_scenario=r.selected_scenario,
                selected_wafi_ppm=(chosen or {}).get("wafi_ppm"),
                selected_wafi_type=(chosen or {}).get("wafi_type"),
                predicted_cfpp_after_wafi=(chosen or {}).get("predicted_cfpp"),
                margin_to_target=(chosen or {}).get("margin_to_target"),
                check_priority=rec.get("check_priority") or [],
                similar_case_ids=[sc.get("case_id", "") for sc in (rec.get("similar_cases") or [])],
                actual_cfpp=actual.get("cfpp"),
                actual_wafi=actual.get("wafi_ppm"),
            )
        )
    return out


class CreateLogBody(BaseModel):
    input: dict
    ai_recommendation: dict
    selected_scenario: str


@router.post("/decision-logs", tags=["dashboard"])
def create_decision_log(body: CreateLogBody, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Create a DecisionLog. Called only when the user finalizes scenario selection."""
    from sqlalchemy import func
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    seq = (
        db.query(func.count(DecisionLog.log_id))
        .filter(DecisionLog.created_at >= today_start)
        .scalar()
        or 0
    ) + 1
    log_id = f"D-{now.strftime('%y%m%d')}-{seq:03d}"
    row = DecisionLog(
        log_id=log_id,
        input=body.input,
        ai_recommendation=body.ai_recommendation,
        selected_scenario=body.selected_scenario,
    )
    db.add(row)
    db.commit()
    return {"log_id": log_id, "selected_scenario": body.selected_scenario}


class SelectScenarioBody(BaseModel):
    label: str


class OutcomeBody(BaseModel):
    actual_cfpp: float | None = None
    actual_wafi: float | None = None


@router.patch("/decision-logs/{log_id}/select-scenario", tags=["dashboard"])
def patch_selected_scenario(log_id: str, body: SelectScenarioBody, db: Session = Depends(get_db)) -> dict[str, Any]:
    row = db.get(DecisionLog, log_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"DecisionLog {log_id} not found")
    row.selected_scenario = body.label
    db.commit()
    return {"log_id": log_id, "selected_scenario": row.selected_scenario}


@router.patch("/decision-logs/{log_id}/outcome", tags=["dashboard"])
def patch_outcome(log_id: str, body: OutcomeBody, db: Session = Depends(get_db)) -> dict[str, Any]:
    row = db.get(DecisionLog, log_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"DecisionLog {log_id} not found")
    outcome = dict(row.actual_outcome or {})
    if body.actual_cfpp is not None:
        outcome["cfpp"] = body.actual_cfpp
    if body.actual_wafi is not None:
        outcome["wafi_ppm"] = body.actual_wafi
    row.actual_outcome = outcome
    # SQLAlchemy needs explicit notification for in-place JSON dict mutation
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(row, "actual_outcome")
    db.commit()
    return {"log_id": log_id, "actual_outcome": outcome}
