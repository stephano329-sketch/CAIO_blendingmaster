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

from typing import Any
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
    # NOTE: do not persist DecisionLog here.
    # Logs are created only when the user explicitly selects a scenario
    # via POST /decision-logs (see backend.routers.dashboard).
    return response


def _persist_decision_log(db: Session, req: JudgeRequest, resp: JudgeResponse, chosen_label: str) -> str | None:
    """Append a row to decision_logs and return the log_id. Best-effort: errors swallowed.

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
        log_id = f"D-{now.strftime('%y%m%d')}-{seq:03d}"
        log = DecisionLog(
            log_id=log_id,
            input=req.model_dump(),
            ai_recommendation=resp.model_dump(),
            selected_scenario=chosen_label,
        )
        db.add(log)
        db.commit()
        return log_id
    except Exception:
        db.rollback()
        return None


# Feature scales for structural similarity (tighter scales = more sensitive)
_STRUCT_SCALES = {
    "lgo_ratio": 0.10,
    "hgo_ratio": 0.10,
    "lco_ratio": 0.05,           # LCO is highly impactful -> small scale = high sensitivity
    "kero_ratio": 0.08,
    "biodiesel_ratio": 0.02,
    "density_15c": 5.0,
    "n_paraffin_c16_c20": 1.5,
    "n_paraffin_c21_plus": 0.8,  # paraffin C21+ very impactful
    "aromatic_content": 3.0,
    "cetane_index": 3.0,
    "target_cfpp": 3.0,
}


def _structural_distance(query: dict, case_row, target_cfpp: float) -> float:
    """Weighted Euclidean distance over blend ratios + key metrics + target CFPP.

    Lower scales = features are weighted more strongly (more sensitive to differences).
    """
    import math
    case_blend = case_row.blend_components or {}
    case_metrics = case_row.key_metrics or {}

    total = 0.0
    n = 0
    blend_keys = ["lgo", "hgo", "lco", "kero", "biodiesel"]
    for k in blend_keys:
        q = query.get(f"{k}_ratio")
        c = case_blend.get(k)
        if q is None or c is None:
            continue
        scale = _STRUCT_SCALES[f"{k}_ratio"]
        total += ((q - c) / scale) ** 2
        n += 1

    metric_keys = ["density_15c", "n_paraffin_c16_c20", "n_paraffin_c21_plus", "aromatic_content", "cetane_index"]
    for k in metric_keys:
        q = query.get(k)
        c = case_metrics.get(k)
        if q is None or c is None:
            continue
        scale = _STRUCT_SCALES[k]
        total += ((q - c) / scale) ** 2
        n += 1

    # target_cfpp difference (penalty)
    cq = target_cfpp
    cc = case_row.target_cfpp
    if cc is not None:
        total += ((cq - cc) / _STRUCT_SCALES["target_cfpp"]) ** 2
        n += 1

    if n == 0:
        return math.inf
    return math.sqrt(total / n)


def _retrieve_similar_cases(req: JudgeRequest, features: dict, db) -> list[SimilarCase]:
    """Hybrid retrieval: vector RAG for broad recall + structural re-ranking for sensitivity.

    Pipeline:
      1. RAG retrieves top-K candidates (broad) constrained to season.
      2. Re-rank by weighted feature distance (blend ratios + key metrics + target CFPP).
      3. Return top-3 most structurally similar cases.
    """
    query_text = (
        f"{req.season} 경유 블렌딩, 목표 CFPP {req.target_cfpp:.1f}°C, "
        f"LGO {features['lgo_ratio']:.2f} HGO {features['hgo_ratio']:.2f} "
        f"LCO {features['lco_ratio']:.2f}, n-파라핀 C21+ {features['n_paraffin_c21_plus']:.2f}wt%, "
        f"탱크 이력 {req.tank_history_flag}, WAFI {features['wafi_type']} {features['wafi_ppm']:.0f}ppm"
    )
    CANDIDATE_K = 20       # broad recall
    FINAL_K = 3            # final top-N returned

    try:
        from backend.engine.rag_retriever import get_retriever
        from backend.models import Case as CaseModel

        retriever = get_retriever()
        if retriever.count() > 0:
            docs = retriever.retrieve_similar_cases(query=query_text, top_k=CANDIDATE_K, season=req.season)
            if not docs:
                docs = retriever.retrieve_similar_cases(query=query_text, top_k=CANDIDATE_K, season=None)

            # Re-rank candidates by structural distance
            candidates: list[tuple[Any, float, float]] = []  # (case_row, struct_dist, rag_sim)
            for d in docs:
                row = db.get(CaseModel, d.doc_id) if d.doc_id else None
                if row is None:
                    continue
                struct_dist = _structural_distance(features, row, req.target_cfpp)
                candidates.append((row, struct_dist, d.similarity_score))

            # Sort by structural distance ascending (closer = more similar)
            candidates.sort(key=lambda x: x[1])
            top = candidates[:FINAL_K]

            out: list[SimilarCase] = []
            for row, struct_dist, rag_sim in top:
                # Blend structural and RAG signals: 70% structural + 30% RAG
                struct_sim = 1.0 / (1.0 + struct_dist)
                hybrid_sim = 0.7 * struct_sim + 0.3 * rag_sim
                out.append(
                    SimilarCase(
                        case_id=row.case_id,
                        decision=row.decision or "normal",
                        similarity_score=round(hybrid_sim, 3),
                        rule_summary=row.rule_summary,
                        blend_components=row.blend_components,
                        key_metrics=row.key_metrics,
                        target_cfpp=row.target_cfpp,
                        season=row.season,
                        tank_history_flag=row.tank_history_flag,
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
