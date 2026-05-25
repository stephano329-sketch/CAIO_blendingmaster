"""
Dataset E-seed — Interview Seed renderer.

Generates 35 cases for the Veteran Knowledge Extraction Agent UI demo.
Same matrix as Dataset D but separate case IDs and re-sampled rows from F.

Each E-seed case has:
- All response fields pre-filled (decision, reason_codes, check_priority,
  risk_codes, rule_summary) — for MVP demo (Decision 4)
- ai_draft_decision and ai_draft_reason_codes — Agent's initial guess shown
  to the veteran at interview start
- No actual_outcome (interview seed, not historical case)

ai_draft vs decision distribution (Decision 5 — Option ④ 21/10/4):
    21 일치 (60%):    Agent guesses correctly
    10 낙관 (29%):    Agent under-estimates risk (draft < decision)
                     - 5 from caution cases (draft=normal)
                     - 5 from risk cases (draft=caution)
     4 과민 (11%):    Agent over-estimates risk (draft > decision)
                     - 3 from normal cases (draft=caution)
                     - 1 from caution case (draft=risk)

Output:
    data/synthetic/interview_seeds.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

from case_renderer import (
    MATRIX,
    derive_check_priority,
    derive_narrative,
    derive_reason_codes,
    derive_risk_codes,
    derive_rule_summary,
    sample_cases,
)


SEED = 20260510
SEED_OFFSET = 2  # different from cases.json seed offset

# Pattern allocation (Decision 5 — Option ④)
DRAFT_PATTERN_ALLOCATION = {
    # decision (true) → list of (count, draft_decision)
    "normal":  [("match",     7, "normal"),
                ("over",      3, "caution")],
    "caution": [("match",     9, "caution"),
                ("under",     5, "normal"),
                ("over",      1, "risk")],
    "risk":    [("match",     5, "risk"),
                ("under",     5, "caution")],
}


def assign_draft_patterns(
    sampled: pd.DataFrame, rng: np.random.Generator
) -> Dict[int, Dict]:
    """Assign (pattern, ai_draft_decision) to each sampled row.

    Returns dict mapping row index → {pattern, draft_decision}.
    """
    assignments: Dict[int, Dict] = {}

    for decision in ["normal", "caution", "risk"]:
        rows = sampled[sampled["decision"] == decision]
        indices = list(rows.index)
        rng.shuffle(indices)

        cursor = 0
        for pattern, count, draft_dec in DRAFT_PATTERN_ALLOCATION[decision]:
            for _ in range(count):
                if cursor >= len(indices):
                    raise RuntimeError(
                        f"Insufficient {decision} rows: need {sum(c for _, c, _ in DRAFT_PATTERN_ALLOCATION[decision])}, "
                        f"have {len(indices)}"
                    )
                idx = indices[cursor]
                assignments[idx] = {
                    "pattern": pattern,
                    "draft_decision": draft_dec,
                }
                cursor += 1
    return assignments


def derive_ai_draft_reason_codes(
    row: pd.Series, draft_decision: str
) -> List[str]:
    """Derive Agent's draft reason codes assuming the draft decision is correct.

    This produces a plausible (but possibly miscalibrated) reasoning chain
    matching the draft decision. The mismatch with veteran's actual reason_codes
    is part of the demo value.
    """
    return derive_reason_codes(row, draft_decision)


def render_seeds(seed: int = SEED) -> List[Dict]:
    project_root = Path(__file__).resolve().parents[2]
    csv_path = project_root / "data" / "synthetic" / "ml_training.csv"
    df = pd.read_csv(csv_path)

    # Sample DIFFERENT rows from F than what cases.json used.
    # We use a different seed offset and let sample_cases naturally pick others.
    # But to guarantee no overlap with D, we exclude D's source_f_index.
    cases_path = project_root / "data" / "synthetic" / "cases.json"
    if cases_path.exists():
        with open(cases_path, "r", encoding="utf-8") as f:
            d_cases = json.load(f)
        d_indices = {c["source_f_index"] for c in d_cases}
        df_for_seeds = df[~df.index.isin(d_indices)]
    else:
        df_for_seeds = df

    rng = np.random.default_rng(seed + SEED_OFFSET)
    sampled = sample_cases(df_for_seeds, rng)

    # Assign draft patterns
    pattern_assignments = assign_draft_patterns(sampled, rng)

    seeds: List[Dict] = []
    for i, (idx, row) in enumerate(sampled.iterrows(), start=1):
        case_id = f"DIESEL-E-{i:03d}"
        decision = str(row["decision"])
        assignment = pattern_assignments[idx]
        draft_decision = assignment["draft_decision"]
        pattern = assignment["pattern"]

        seed_case = {
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

            # AI Agent's initial draft (shown to veteran at interview start)
            "ai_draft_decision": draft_decision,
            "ai_draft_reason_codes": derive_ai_draft_reason_codes(row, draft_decision),

            # Veteran's final answer (pre-filled for MVP demo)
            "decision": decision,
            "reason_codes": derive_reason_codes(row, decision),
            "check_priority": derive_check_priority(row, decision),
            "risk_codes": derive_risk_codes(row, decision),
            "rule_summary": derive_rule_summary(row, decision),

            # Demo metadata
            "draft_pattern": pattern,
            "narrative": derive_narrative(row, decision, case_id),
        }
        seeds.append(seed_case)

    return seeds


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    out_path = project_root / "data" / "synthetic" / "interview_seeds.json"

    seeds = render_seeds()

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(seeds, f, indent=2, ensure_ascii=False)

    pattern_counts = {"match": 0, "under": 0, "over": 0}
    for s in seeds:
        pattern_counts[s["draft_pattern"]] += 1

    decision_counts = {}
    for s in seeds:
        d = s["decision"]
        decision_counts.setdefault(d, 0)
        decision_counts[d] += 1

    print(f"Wrote {len(seeds)} interview seeds to {out_path}")
    print(f"  pattern distribution: {pattern_counts}")
    print(f"  decision distribution: {decision_counts}")
    print(f"  expected (Decision 5 ④): match=21, under=10, over=4")


if __name__ == "__main__":
    main()
