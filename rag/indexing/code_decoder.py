"""
Code system decoder — PRD Appendix A 25-code mapping.

Provides bi-directional translation between English codes (storage form)
and Korean display labels (RAG search and UI form).

Categories:
    decision     — Q1 판단 (3 codes)
    reason       — Q2 판단 근거 (9 codes)
    check        — Q3 확인 우선순위 (7 codes)
    risk         — Q4 리스크 포인트 (6 codes)

Total: 25 codes (per PRD Appendix A and BRD §8).

Usage:
    from rag.indexing.code_decoder import decode_decision, decode_reasons, decode_checks, decode_risks

    decode_decision("caution")            # → "주의"
    decode_reasons(["tank_history"])      # → ["저장탱크 이력"]
    decode_checks(["retest", "blend_ratio"])  # → ["검사 재확인", "반제품 비율 확인"]
"""

from __future__ import annotations

from typing import Dict, Iterable, List


# =============================================================================
# Decision codes (Q1)
# =============================================================================
DECISION_KO: Dict[str, str] = {
    "normal":  "정상",
    "caution": "주의",
    "risk":    "위험",
}

DECISION_DESCRIPTION_KO: Dict[str, str] = {
    "normal":  "출하 및 운용에 문제 없음",
    "caution": "조건에 따라 리스크가 있어 추가 확인 필요",
    "risk":    "문제 발생 가능성이 높아 조치 필요",
}


# =============================================================================
# Reason codes (Q2 — 판단 근거)
# =============================================================================
REASON_KO: Dict[str, str] = {
    "metric_level":           "검사값 절대 수준",
    "metric_variability":     "검사값 변동성",
    "blend_component":        "반제품 구성 영향",
    "process_change":         "공정 조건 변화",
    "tank_history":           "저장탱크 이력",
    "seasonality":            "계절 영향",
    "additive":               "첨가제 영향",
    "inspection_reliability": "검사 신뢰도 문제",
    "other":                  "기타",
}


# =============================================================================
# Check codes (Q3 — 확인 우선순위)
# =============================================================================
CHECK_KO: Dict[str, str] = {
    "retest":            "검사 재확인",
    "blend_ratio":       "반제품 비율 확인",
    "process_condition": "공정 조건 확인",
    "tank_history":      "탱크 이력 확인",
    "additive_dose":     "첨가제 투입량 확인",
    "equipment_status":  "설비 상태 점검",
    "other":             "기타",
}


# =============================================================================
# Risk codes (Q4 — 리스크 포인트)
# =============================================================================
RISK_KO: Dict[str, str] = {
    "within_spec_but_risky":        "기준 내지만 위험 가능성 있음",
    "conditional_quality_risk":     "특정 조건에서 품질 악화 가능",
    "inspection_reliability_issue": "검사값 신뢰도 문제",
    "historical_impact":            "이력 영향 가능성",
    "post_issue_possible":          "출하 후 문제 발생 가능",
    "other":                        "기타",
}


# =============================================================================
# Reverse mappings (Korean → English) for query parsing
# =============================================================================
DECISION_EN: Dict[str, str] = {v: k for k, v in DECISION_KO.items()}
REASON_EN:   Dict[str, str] = {v: k for k, v in REASON_KO.items()}
# Note: CHECK and RISK have potentially overlapping keys (e.g., "tank_history"
# appears in both reason and check). We use namespace-aware reverse mappings.


# =============================================================================
# Decoder API
# =============================================================================
def decode_decision(code: str) -> str:
    """Translate a single decision code to Korean."""
    if code not in DECISION_KO:
        raise KeyError(f"Unknown decision code: {code!r}")
    return DECISION_KO[code]


def decode_reasons(codes: Iterable[str]) -> List[str]:
    """Translate reason codes to Korean labels (preserves order, drops unknown)."""
    return [REASON_KO[c] for c in codes if c in REASON_KO]


def decode_checks(codes: Iterable[str]) -> List[str]:
    """Translate check codes to Korean labels."""
    return [CHECK_KO[c] for c in codes if c in CHECK_KO]


def decode_risks(codes: Iterable[str]) -> List[str]:
    """Translate risk codes to Korean labels."""
    return [RISK_KO[c] for c in codes if c in RISK_KO]


def encode_decision(label_ko: str) -> str:
    """Reverse: Korean decision label → English code."""
    if label_ko not in DECISION_EN:
        raise KeyError(f"Unknown decision label: {label_ko!r}")
    return DECISION_EN[label_ko]


def encode_reason(label_ko: str) -> str:
    """Reverse: Korean reason label → English code."""
    if label_ko not in REASON_EN:
        raise KeyError(f"Unknown reason label: {label_ko!r}")
    return REASON_EN[label_ko]


def all_codes() -> Dict[str, Dict[str, str]]:
    """Return all 25 codes grouped by category — for inspection or export."""
    return {
        "decision": dict(DECISION_KO),
        "reason":   dict(REASON_KO),
        "check":    dict(CHECK_KO),
        "risk":     dict(RISK_KO),
    }


def total_code_count() -> int:
    return (
        len(DECISION_KO) + len(REASON_KO) + len(CHECK_KO) + len(RISK_KO)
    )


if __name__ == "__main__":
    import json

    print(f"Total codes: {total_code_count()}")
    print(json.dumps(all_codes(), indent=2, ensure_ascii=False))

    # Sanity examples
    print()
    print("decode_decision('caution') =", decode_decision("caution"))
    print(
        "decode_reasons(['metric_variability', 'tank_history']) =",
        decode_reasons(["metric_variability", "tank_history"]),
    )
    print(
        "decode_checks(['retest', 'blend_ratio', 'tank_history']) =",
        decode_checks(["retest", "blend_ratio", "tank_history"]),
    )
    print(
        "decode_risks(['within_spec_but_risky', 'post_issue_possible']) =",
        decode_risks(["within_spec_but_risky", "post_issue_possible"]),
    )
