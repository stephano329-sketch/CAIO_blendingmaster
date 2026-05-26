"""Recommendation service: orchestrates ML prediction + WAFI scenario search.

For Phase 1 the pipeline is:
    1. Build feature dict from JudgeRequest
    2. Predict baseline CFPP at wafi_ppm = 0
    3. Sweep WAFI ppm grid to find ppm hitting target_cfpp with chosen margin
    4. Generate 3 scenarios (min_cost / balanced / safe)
    5. Pull top-3 similar cases from the DB
    6. Decide normal / caution / risk based on margin and similar case majority
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from backend.engine.ml_predictor import get_predictor
from backend.engine.similar_cases import find_similar_cases, distance_to_similarity
from backend.schemas.judge import (
    JudgeRequest,
    JudgeResponse,
    WafiScenario,
    SimilarCase,
)

PPM_GRID = list(range(0, 1001, 25))  # 0, 25, 50, ..., 1000 ppm

SCENARIO_MARGINS = {
    "min_cost": 1.0,   # +1°C below target (cheapest viable)
    "balanced": 3.0,   # +3°C safety margin
    "safe": 5.0,       # +5°C extra margin
}


def _build_features(req: JudgeRequest) -> dict:
    bc = req.blend_components
    km = req.key_metrics
    return {
        "lgo_ratio": bc.lgo,
        "hgo_ratio": bc.hgo,
        "lco_ratio": bc.lco,
        "kero_ratio": bc.kero,
        "biodiesel_ratio": bc.biodiesel,
        "density_15c": km.density_15c,
        "n_paraffin_c10_c15": km.n_paraffin_c10_c15,
        "n_paraffin_c16_c20": km.n_paraffin_c16_c20,
        "n_paraffin_c21_plus": km.n_paraffin_c21_plus,
        "aromatic_content": km.aromatic_content,
        "sulfur_ppm": km.sulfur_ppm,
        "cetane_index": km.cetane_index,
        "wafi_type": km.wafi_type,
        "wafi_ppm": km.wafi_ppm,
        "season": req.season,
        "tank_history_flag": req.tank_history_flag,
    }


def _select_ppm_for_margin(
    sweep: list[tuple[float, float]],
    target_cfpp: float,
    desired_margin: float,
) -> tuple[float, float]:
    """Find smallest ppm whose predicted CFPP <= target_cfpp - desired_margin.

    Returns (selected_ppm, predicted_cfpp). If nothing meets the margin,
    returns the highest-ppm sample with its prediction.
    """
    threshold = target_cfpp - desired_margin
    for ppm, pred in sweep:
        if pred <= threshold:
            return ppm, pred
    return sweep[-1]


def _decide(margin: float, similar_decisions: list[str]) -> tuple[str, float]:
    """Decide normal/caution/risk from margin + similar-case majority vote.

    Confidence combines two real signals:
      1. Similar-case agreement: fraction of top-K cases that match the final decision.
      2. Margin distance from decision boundary: how far we are from a class flip.
         - normal:  boundary at margin = 3.0  (higher margin = more confident normal)
         - caution: bands [1.0, 3.0]          (center = 2.0 most confident)
         - risk:    boundary at margin = 1.0  (more negative = more confident risk)
    Final confidence = 0.5 × agreement + 0.5 × margin_signal, clamped to [0.30, 0.95].
    """
    base = "normal" if margin >= 3.0 else "caution" if margin >= 1.0 else "risk"

    decision = base
    if similar_decisions:
        risk_n = similar_decisions.count("risk")
        caution_n = similar_decisions.count("caution")
        if risk_n >= max(1, len(similar_decisions) // 2):
            decision = "risk"
        elif caution_n >= max(1, len(similar_decisions) // 2) and base == "normal":
            decision = "caution"

    # Signal 1: similar-case agreement with final decision
    n_total = len(similar_decisions)
    if n_total > 0:
        n_agree = similar_decisions.count(decision)
        agreement = n_agree / n_total
    else:
        agreement = 0.5  # neutral when no similar cases

    # Signal 2: distance from decision boundary, mapped to [0, 1]
    if decision == "normal":
        # margin >= 3 required; further above = stronger
        margin_signal = max(0.0, min(1.0, (margin - 3.0) / 5.0 + 0.5))
    elif decision == "caution":
        # band [1, 3]; peak confidence at margin = 2.0
        margin_signal = max(0.0, min(1.0, 1.0 - abs(margin - 2.0) / 2.0))
    else:  # risk
        # margin < 1; the more negative, the more confident risk
        margin_signal = max(0.0, min(1.0, (1.0 - margin) / 5.0 + 0.3))

    confidence = 0.5 * agreement + 0.5 * margin_signal
    confidence = max(0.30, min(0.95, confidence))
    return decision, confidence


def _check_priority_for(decision: str, season: str, tank_history: str) -> list[str]:
    priority = []
    if decision in ("caution", "risk"):
        priority.append("retest")
    priority.append("blend_ratio")
    priority.append("additive_dose")
    if tank_history != "clean":
        priority.insert(0, "tank_history")
    if season == "deep_winter":
        priority.append("process_condition")
    seen = set()
    deduped = []
    for p in priority:
        if p not in seen:
            deduped.append(p)
            seen.add(p)
    return deduped[:3]


def judge(req: JudgeRequest, db: Session) -> JudgeResponse:
    predictor = get_predictor()
    features = _build_features(req)

    baseline_features = dict(features, wafi_ppm=0.0)
    baseline_cfpp = predictor.predict(baseline_features)

    sweep = predictor.predict_with_wafi_sweep(
        features, PPM_GRID, wafi_type=req.key_metrics.wafi_type or "A"
    )

    scenarios: list[WafiScenario] = []
    for label, margin in SCENARIO_MARGINS.items():
        ppm, pred = _select_ppm_for_margin(sweep, req.target_cfpp, margin)
        actual_margin = req.target_cfpp - pred
        scenarios.append(
            WafiScenario(
                label=label,
                wafi_type=req.key_metrics.wafi_type or "A",
                wafi_ppm=float(ppm),
                predicted_cfpp=round(pred, 2),
                margin_to_target=round(actual_margin, 2),
                confidence=round(max(0.3, min(0.95, 0.4 + 0.1 * actual_margin)), 2),
                rationale=_scenario_rationale(label, ppm, actual_margin, margin),
            )
        )

    similar_cases = _retrieve_similar_cases(req, features, db)

    priority_to_label = {"cost": "min_cost", "balance": "balanced", "safety": "safe"}
    chosen_label = priority_to_label.get(req.priority, "balanced")
    chosen = next((s for s in scenarios if s.label == chosen_label), scenarios[1])
    decision, confidence = _decide(
        margin=chosen.margin_to_target,
        similar_decisions=[sc.decision for sc in similar_cases],
    )

    response = JudgeResponse(
        decision=decision,
        predicted_cfpp_baseline=round(baseline_cfpp, 2),
        confidence=round(confidence, 2),
        scenarios=scenarios,
        check_priority=_check_priority_for(decision, req.season, req.tank_history_flag),
        similar_cases=similar_cases,
        applied_heuristics=[],
    )

    _persist_decision_log(db, req, response, chosen_label)
    return response


def _persist_decision_log(db: Session, req: JudgeRequest, resp: JudgeResponse, chosen_label: str) -> None:
    """Append a row to decision_logs for dashboard reporting. Best-effort: errors swallowed.

    log_id format: D-YYMMDD-NNN (NNN = today's sequence number, zero-padded).
    """
    from datetime import datetime
    from sqlalchemy import func
    from backend.models import DecisionLog

    try:
        now = datetime.utcnow()
        today_start = datetime(now.year, now.month, now.day)
        seq = (
            db.query(func.count(DecisionLog.log_id))
            .filter(DecisionLog.created_at >= today_start)
            .scalar()
            or 0
        ) + 1
        log = DecisionLog(
            log_id=f"D-{now.strftime('%y%m%d')}-{seq:03d}",
            input=req.model_dump(),
            ai_recommendation=resp.model_dump(),
            selected_scenario=chosen_label,
        )
        db.add(log)
        db.commit()
    except Exception:
        db.rollback()


def _retrieve_similar_cases(req: JudgeRequest, features: dict, db) -> list[SimilarCase]:
    """Prefer RAG (vector) retrieval; fall back to numeric distance over Case rows."""
    query = (
        f"{req.season} 경유 블렌딩, 목표 CFPP {req.target_cfpp:.1f}°C, "
        f"LGO {features['lgo_ratio']:.2f} HGO {features['hgo_ratio']:.2f} "
        f"LCO {features['lco_ratio']:.2f}, n-파라핀 C21+ {features['n_paraffin_c21_plus']:.2f}wt%, "
        f"탱크 이력 {req.tank_history_flag}, WAFI {features['wafi_type']} {features['wafi_ppm']:.0f}ppm"
    )
    try:
        from backend.engine.rag_retriever import get_retriever

        retriever = get_retriever()
        if retriever.count() > 0:
            docs = retriever.retrieve_similar_cases(query=query, top_k=3, season=req.season)
            if not docs:
                docs = retriever.retrieve_similar_cases(query=query, top_k=3, season=None)
            from backend.models import Case as CaseModel

            out: list[SimilarCase] = []
            for d in docs:
                row = db.get(CaseModel, d.doc_id) if d.doc_id else None
                out.append(
                    SimilarCase(
                        case_id=d.doc_id,
                        decision=(row.decision if row else d.metadata.get("decision", "normal")),
                        similarity_score=round(d.similarity_score, 3),
                        rule_summary=(row.rule_summary if row else None),
                        blend_components=(row.blend_components if row else None),
                        key_metrics=(row.key_metrics if row else None),
                        target_cfpp=(row.target_cfpp if row else None),
                        season=(row.season if row else None),
                        tank_history_flag=(row.tank_history_flag if row else None),
                    )
                )
            if out:
                return out
    except Exception:
        # ChromaDB unavailable -> fall through to numeric distance
        pass

    similar_pairs = find_similar_cases(
        db,
        query_metrics=features,
        target_cfpp=req.target_cfpp,
        season=req.season,
        top_k=3,
    )
    return [
        SimilarCase(
            case_id=c.case_id,
            decision=c.decision,
            similarity_score=round(distance_to_similarity(dist), 3),
            rule_summary=c.rule_summary,
            blend_components=c.blend_components,
            key_metrics=c.key_metrics,
            target_cfpp=c.target_cfpp,
            season=c.season,
            tank_history_flag=c.tank_history_flag,
        )
        for c, dist in similar_pairs
    ]


def _scenario_rationale(label: str, ppm: float, actual_margin: float, desired_margin: float) -> str:
    if actual_margin < desired_margin:
        return (
            f"PPM 그리드 한계({int(ppm)}ppm)에서 "
            f"마진 {actual_margin:.1f}°C — 목표 마진 {desired_margin:.1f}°C 미달, "
            f"반제품 구성 재검토 필요"
        )
    return (
        f"{int(ppm)}ppm 투입 시 목표 대비 "
        f"마진 {actual_margin:.1f}°C 확보"
    )
