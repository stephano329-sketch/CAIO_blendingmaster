"""
Dataset D — Case Knowledge renderer.

Samples 35 rows from Dataset F (`ml_training.csv`) according to the matrix:
            winter   deep_winter   total
normal       5         5            10
caution      8         7            15
risk         5         5            10
                                    ---
                                     35

For each sampled case, generates:
- Structured fields: case_id, context, decision, reason_codes, check_priority,
  risk_codes, rule_summary, actual_outcome
- A natural-language narrative for RAG embedding

`actual_outcome.off_spec` rates (Decision 6):
    normal:  0%   (0/10)
    caution: 25%  (~4/15, randomly selected)
    risk:    60%  (~6/10, randomly selected)

Output:
    data/synthetic/cases.json
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


# =============================================================================
# Configuration
# =============================================================================
SEED = 20260510
MATRIX = {
    ("winter",      "normal"):  5,
    ("winter",      "caution"): 8,
    ("winter",      "risk"):    5,
    ("deep_winter", "normal"):  5,
    ("deep_winter", "caution"): 7,
    ("deep_winter", "risk"):    5,
}

OFF_SPEC_RATES = {
    "normal":  0.00,
    "caution": 0.25,  # ~4 of 15
    "risk":    0.60,  # ~6 of 10
}

REWORK_RATE_OF_OFFSPEC = 0.80  # 80% of off_spec cases need rework


# =============================================================================
# Reason / check / risk code generation logic
# =============================================================================
def derive_reason_codes(row: pd.Series, decision: str) -> List[str]:
    """Derive reason codes from row features and decision."""
    reasons: List[str] = []

    # n-paraffin variability is a frequent caution/risk reason
    if row["n_paraffin_c21_plus"] > 3.0:
        reasons.append("metric_variability")

    # Tank history matters
    if row["tank_history_flag"] in ("recent_change", "mixed"):
        reasons.append("tank_history")

    # LCO content high → blend component issue
    if row["lco_ratio"] > 0.12:
        reasons.append("blend_component")

    # WAFI under-dose → additive issue
    if decision in ("caution", "risk") and row["wafi_ppm"] < 150:
        reasons.append("additive")

    # Seasonality: deep_winter is always a stress factor
    if row["season"] == "deep_winter" and decision in ("caution", "risk"):
        reasons.append("seasonality")

    # Metric level: if cfpp is close to or above target
    margin = row["target_cfpp"] - row["cfpp"]
    if margin < 1.0:
        reasons.append("metric_level")

    # Limit to max 2 reasons (per BRD §7 rule)
    if not reasons:
        if decision == "normal":
            reasons = ["metric_level"]
        else:
            reasons = ["metric_variability"]

    return reasons[:2]


def derive_check_priority(row: pd.Series, decision: str) -> List[str]:
    """Top-3 check priorities."""
    checks: List[str] = []

    if row["tank_history_flag"] != "clean":
        checks.append("tank_history")

    if row["wafi_ppm"] < 200:
        checks.append("additive_dose")

    if row["lco_ratio"] > 0.10 or row["hgo_ratio"] > 0.20:
        checks.append("blend_ratio")

    if row["n_paraffin_c21_plus"] > 2.5:
        checks.append("retest")

    # Default order
    fallback = ["retest", "blend_ratio", "additive_dose", "tank_history",
                "process_condition", "equipment_status"]
    for f in fallback:
        if f not in checks:
            checks.append(f)
        if len(checks) == 3:
            break
    return checks[:3]


def derive_risk_codes(row: pd.Series, decision: str) -> List[str]:
    if decision == "normal":
        return []
    risks: List[str] = []
    margin = row["target_cfpp"] - row["cfpp"]

    if 0 <= margin < 2:
        risks.append("within_spec_but_risky")

    if row["season"] == "deep_winter":
        risks.append("conditional_quality_risk")

    if row["tank_history_flag"] != "clean":
        risks.append("historical_impact")

    if decision == "risk" and margin < 0:
        risks.append("post_issue_possible")

    if row["n_paraffin_c21_plus"] > 3.0:
        risks.append("inspection_reliability_issue")

    if not risks:
        risks = ["within_spec_but_risky"]

    return risks[:3]


def derive_rule_summary(row: pd.Series, decision: str) -> str:
    """Compose a 1-2 sentence one-line judgment rule."""
    season_kr = "동절기" if row["season"] == "winter" else "혹한기"
    if decision == "normal":
        return f"{season_kr} 표준 조건 — 검사값 안정, WAFI 적정 → 출하 가능"
    if decision == "caution":
        bits = []
        if row["tank_history_flag"] != "clean":
            bits.append("탱크 이력 변동")
        if row["n_paraffin_c21_plus"] > 3.0:
            bits.append("n-파라핀 C21+ 변동성")
        if row["wafi_ppm"] < 200:
            bits.append("WAFI 마진 협소")
        if not bits:
            bits = ["검사값 경계 근접"]
        return f"{season_kr} 주의 — {' + '.join(bits)} → 재확인 후 출하 결정"
    # risk
    bits = []
    if row["target_cfpp"] - row["cfpp"] < 0:
        bits.append("CFPP 목표 미달")
    if row["n_paraffin_c21_plus"] > 3.5:
        bits.append("C21+ 과다")
    if row["wafi_ppm"] < 150:
        bits.append("WAFI 부족")
    if not bits:
        bits = ["다중 위험 신호"]
    return f"{season_kr} 위험 — {' + '.join(bits)} → WAFI 증량 또는 재블렌딩 필요"


def derive_narrative(row: pd.Series, decision: str, case_id: str) -> str:
    """Generate RAG-embedding-friendly Korean narrative."""
    season_kr = "동절기" if row["season"] == "winter" else "혹한기"
    blend_str = (
        f"LGO {row['lgo_ratio']:.2f} / HGO {row['hgo_ratio']:.2f} / "
        f"LCO {row['lco_ratio']:.2f} / Kero {row['kero_ratio']:.2f} / "
        f"Bio 0.03"
    )
    decision_kr = {"normal": "정상", "caution": "주의", "risk": "위험"}[decision]
    margin = row["target_cfpp"] - row["cfpp"]

    parts = [
        f"케이스 {case_id} — {season_kr} 생산.",
        f"반제품 구성: {blend_str}.",
        f"주요 검사값: 측정 CFPP {row['cfpp']:.1f}°C, 목표 CFPP {row['target_cfpp']:.1f}°C "
        f"(마진 {margin:+.1f}°C), n-파라핀 C16-20 {row['n_paraffin_c16_c20']:.1f}wt%, "
        f"C21+ {row['n_paraffin_c21_plus']:.2f}wt%, 밀도 15°C {row['density_15c']:.0f} kg/m³.",
        f"첨가제: {row['wafi_type']} 타입 {row['wafi_ppm']:.0f}ppm.",
        f"탱크 이력: {row['tank_history_flag']}.",
        f"베테랑 판단: {decision_kr}.",
    ]
    return " ".join(parts)


def derive_actual_outcome(
    row: pd.Series, decision: str, off_spec: bool, rng: np.random.Generator
) -> Dict:
    """Generate sufficient post-batch outcome data."""
    initial_wafi = float(row["wafi_ppm"])
    if off_spec:
        # Off-spec: WAFI was bumped 50-150ppm to recover
        adjusted = min(500.0, initial_wafi + float(rng.uniform(50, 150)))
        rework_required = bool(rng.random() < REWORK_RATE_OF_OFFSPEC)
        # Final CFPP is near target (success after rework) or still over (failure)
        if rework_required:
            final_cfpp = float(row["target_cfpp"]) + float(rng.uniform(-1.5, 1.5))
        else:
            # Remained off-spec, accepted with downgrade or product reclassification
            final_cfpp = float(row["cfpp"]) + float(rng.uniform(-0.5, 1.5))
    else:
        # Pass: WAFI adjusted ±50ppm during fine-tuning
        adjusted = max(0.0, min(500.0,
                                 initial_wafi + float(rng.uniform(-30, 30))))
        rework_required = False
        final_cfpp = float(row["cfpp"]) + float(rng.uniform(-1.0, 1.0))

    return {
        "final_cfpp": round(final_cfpp, 1),
        "off_spec": bool(off_spec),
        "rework_required": rework_required,
        "wafi_adjusted_to": round(adjusted, 0),
    }


# =============================================================================
# Sampling and main pipeline
# =============================================================================
def sample_cases(
    df: pd.DataFrame, rng: np.random.Generator
) -> pd.DataFrame:
    """Sample 35 rows from F matching the D matrix.

    Strategy: for each (season, decision) cell, randomly pick the required count
    from rows in F that match (using `decision` not `decision_noisy`).
    Strives for diversity by avoiding monotonicity-pair indices when possible.
    """
    chunks = []
    used_indices = set()
    for (season, decision), needed in MATRIX.items():
        candidates = df[(df["season"] == season) & (df["decision"] == decision)]
        candidates = candidates[~candidates.index.isin(used_indices)]
        if len(candidates) < needed:
            raise RuntimeError(
                f"Insufficient F rows for ({season}, {decision}): "
                f"need {needed}, have {len(candidates)}"
            )
        picked_idx = rng.choice(candidates.index, size=needed, replace=False)
        chunks.append(df.loc[picked_idx].copy())
        used_indices.update(picked_idx)
    return pd.concat(chunks, ignore_index=False)


def render_cases(seed: int = SEED) -> List[Dict]:
    project_root = Path(__file__).resolve().parents[2]
    csv_path = project_root / "data" / "synthetic" / "ml_training.csv"
    df = pd.read_csv(csv_path)

    rng = np.random.default_rng(seed + 1)
    sampled = sample_cases(df, rng)

    # Decide off_spec by decision class with target counts
    off_spec_assignments: List[bool] = []
    for decision in ["normal", "caution", "risk"]:
        n_in_class = (sampled["decision"] == decision).sum()
        n_off_spec = int(round(n_in_class * OFF_SPEC_RATES[decision]))
        flags = [True] * n_off_spec + [False] * (n_in_class - n_off_spec)
        rng.shuffle(flags)
        off_spec_assignments.append((decision, flags))

    # Build off_spec map per row
    off_spec_map: Dict[int, bool] = {}
    for decision, flags in off_spec_assignments:
        rows = sampled[sampled["decision"] == decision]
        for idx, flag in zip(rows.index, flags):
            off_spec_map[idx] = flag

    cases: List[Dict] = []
    for i, (idx, row) in enumerate(sampled.iterrows(), start=1):
        case_id = f"DIESEL-D-{i:03d}"
        decision = str(row["decision"])
        off_spec = off_spec_map[idx]

        case = {
            "case_id": case_id,
            "source_f_index": int(idx),
            "context": {
                "season": str(row["season"]),
                "blend_components": {
                    "lgo": round(float(row["lgo_ratio"]), 4),
                    "hgo": round(float(row["hgo_ratio"]), 4),
                    "lco": round(float(row["lco_ratio"]), 4),
                    "kero": round(float(row["kero_ratio"]), 4),
                    "biodiesel": round(float(row["biodiesel_ratio"]), 4),
                },
                "key_metrics": {
                    "cfpp_measured": round(float(row["cfpp"]), 1),
                    "cp": round(float(row["cp"]), 1),
                    "pp": round(float(row["pp"]), 1),
                    "density_15c": round(float(row["density_15c"]), 1),
                    "n_paraffin_c10_c15": round(float(row["n_paraffin_c10_c15"]), 2),
                    "n_paraffin_c16_c20": round(float(row["n_paraffin_c16_c20"]), 2),
                    "n_paraffin_c21_plus": round(float(row["n_paraffin_c21_plus"]), 2),
                    "aromatic_content": round(float(row["aromatic_content"]), 1),
                    "sulfur_ppm": round(float(row["sulfur_ppm"]), 1),
                    "cetane_index": round(float(row["cetane_index"]), 1),
                    "wafi_type": str(row["wafi_type"]),
                    "wafi_ppm": round(float(row["wafi_ppm"]), 0),
                },
                "target_cfpp": round(float(row["target_cfpp"]), 1),
                "tank_history_flag": str(row["tank_history_flag"]),
            },
            "decision": decision,
            "reason_codes": derive_reason_codes(row, decision),
            "check_priority": derive_check_priority(row, decision),
            "risk_codes": derive_risk_codes(row, decision),
            "rule_summary": derive_rule_summary(row, decision),
            "actual_outcome": derive_actual_outcome(row, decision, off_spec, rng),
            "narrative": derive_narrative(row, decision, case_id),
        }
        cases.append(case)

    return cases


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    out_path = project_root / "data" / "synthetic" / "cases.json"

    cases = render_cases()

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2, ensure_ascii=False)

    n_off_spec = sum(1 for c in cases if c["actual_outcome"]["off_spec"])
    print(f"Wrote {len(cases)} cases to {out_path}")
    print(f"  off_spec count: {n_off_spec}")
    by_decision = {}
    for c in cases:
        d = c["decision"]
        by_decision.setdefault(d, {"total": 0, "off_spec": 0})
        by_decision[d]["total"] += 1
        if c["actual_outcome"]["off_spec"]:
            by_decision[d]["off_spec"] += 1
    print(f"  by decision: {by_decision}")


if __name__ == "__main__":
    main()
