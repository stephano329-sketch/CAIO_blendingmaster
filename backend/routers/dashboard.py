"""Dashboard aggregate endpoints (stats + recent decision logs)."""
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
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
                pred_cfpp=float(rec.get("predicted_cfpp_baseline", 0.0)),
                wafi_suggested=float((chosen or {}).get("wafi_ppm", 0.0)),
                actual_cfpp=actual.get("cfpp"),
                actual_wafi=actual.get("wafi_ppm"),
                decision=rec.get("decision", "normal"),
                selected_scenario=r.selected_scenario,
            )
        )
    return out
