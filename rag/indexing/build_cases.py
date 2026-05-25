"""
Build Dataset D (cases.json) into RAG chunks for the primary collection.

For each case in `data/synthetic/cases.json`, produces a single chunk with:
- Rich Korean narrative including blend, metrics, decision rationale, and
  post-batch outcome — all RAG-embedding-friendly
- English code metadata for filtering (decision, season, reason_codes)
- Korean-decoded labels in the document text for query matching
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from rag.indexing.build_documents import Chunk
from rag.indexing.code_decoder import (
    decode_checks,
    decode_decision,
    decode_reasons,
    decode_risks,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CASES_PATH = PROJECT_ROOT / "data" / "synthetic" / "cases.json"


def _format_blend(components: Dict[str, float]) -> str:
    parts = [
        f"LGO {components['lgo']:.2f}",
        f"HGO {components['hgo']:.2f}",
        f"LCO {components['lco']:.2f}",
        f"Kero {components['kero']:.2f}",
        f"Bio {components['biodiesel']:.2f}",
    ]
    return " / ".join(parts)


def _format_season(season: str) -> str:
    return {"winter": "동절기", "deep_winter": "혹한기"}.get(season, season)


def _build_document_text(case: Dict) -> str:
    """Compose RAG-friendly Korean text from case JSON.

    Includes both English codes and Korean labels in the body so that
    queries in either form can match.
    """
    ctx = case["context"]
    metrics = ctx["key_metrics"]
    decision = case["decision"]
    decision_ko = decode_decision(decision)
    season_ko = _format_season(ctx["season"])
    reasons_ko = decode_reasons(case["reason_codes"])
    checks_ko = decode_checks(case["check_priority"])
    risks_ko = decode_risks(case["risk_codes"])

    margin = ctx["target_cfpp"] - metrics["cfpp_measured"]
    outcome = case["actual_outcome"]
    outcome_text = (
        f"final CFPP {outcome['final_cfpp']:.1f}°C, "
        f"off-spec {'발생' if outcome['off_spec'] else '없음'}, "
        f"WAFI 최종 {outcome['wafi_adjusted_to']:.0f}ppm"
    )
    if outcome["rework_required"]:
        outcome_text += ", 재블렌딩 수행"

    lines = [
        f"[케이스 {case['case_id']}] — {season_ko} 생산, 베테랑 판단 {decision_ko}",
        "",
        f"반제품 구성: {_format_blend(ctx['blend_components'])}",
        f"주요 검사값:",
        f"  - 측정 CFPP {metrics['cfpp_measured']:.1f}°C, "
        f"목표 CFPP {ctx['target_cfpp']:.1f}°C (마진 {margin:+.1f}°C)",
        f"  - CP {metrics['cp']:.1f}°C, PP {metrics['pp']:.1f}°C",
        f"  - 밀도 15°C {metrics['density_15c']:.0f} kg/m³",
        f"  - n-파라핀 C10-15 {metrics['n_paraffin_c10_c15']:.1f}wt%, "
        f"C16-20 {metrics['n_paraffin_c16_c20']:.1f}wt%, "
        f"C21+ {metrics['n_paraffin_c21_plus']:.2f}wt%",
        f"  - 방향족 {metrics['aromatic_content']:.1f}vol%, "
        f"세탄 지수 {metrics['cetane_index']:.1f}, "
        f"황분 {metrics['sulfur_ppm']:.1f}ppm",
        f"첨가제: {metrics['wafi_type']} 타입 {metrics['wafi_ppm']:.0f}ppm",
        f"탱크 이력: {ctx['tank_history_flag']}",
        "",
        f"베테랑 판단: {decision_ko} ({decision})",
        f"판단 근거: {', '.join(reasons_ko) if reasons_ko else '없음'} "
        f"[{', '.join(case['reason_codes'])}]",
        f"확인 우선순위: {' → '.join(checks_ko) if checks_ko else '없음'} "
        f"[{', '.join(case['check_priority'])}]",
        f"리스크 포인트: {', '.join(risks_ko) if risks_ko else '없음'} "
        f"[{', '.join(case['risk_codes']) if case['risk_codes'] else '없음'}]",
        f"한 줄 기준: {case['rule_summary']}",
        "",
        f"사후 결과: {outcome_text}",
    ]
    return "\n".join(lines)


def _build_metadata(case: Dict) -> Dict[str, str]:
    """ChromaDB metadata — primitive types only, used for filter queries."""
    ctx = case["context"]
    return {
        "doc_type":           "case",
        "lang":               "ko",
        "version":            "1.0",
        "source":             "synthetic",
        "case_id":            case["case_id"],
        "season":             ctx["season"],
        "decision":           case["decision"],
        # Comma-joined for ChromaDB primitive constraint; multi-value filter
        # works via $in or LIKE in retrieval layer.
        "reason_codes":       ",".join(case["reason_codes"]),
        "check_priority":     ",".join(case["check_priority"]),
        "risk_codes":         ",".join(case["risk_codes"]),
        "off_spec":           bool(case["actual_outcome"]["off_spec"]),
        "rework_required":    bool(case["actual_outcome"]["rework_required"]),
        "source_f_index":     int(case["source_f_index"]),
        "wafi_type":          str(ctx["key_metrics"]["wafi_type"]),
    }


def build_case_chunks() -> List[Chunk]:
    if not CASES_PATH.exists():
        raise FileNotFoundError(
            f"{CASES_PATH} not found. Run ml/data_generation/case_renderer.py first."
        )
    with open(CASES_PATH, encoding="utf-8") as f:
        cases = json.load(f)

    chunks: List[Chunk] = []
    for case in cases:
        chunk = Chunk(
            id=f"case:{case['case_id']}",
            document=_build_document_text(case),
            metadata=_build_metadata(case),
        )
        chunks.append(chunk)
    return chunks


def main() -> None:
    chunks = build_case_chunks()
    print(f"Built {len(chunks)} case chunks")

    # Distribution
    by_decision: Dict[str, int] = {}
    by_season: Dict[str, int] = {}
    for c in chunks:
        by_decision.setdefault(c.metadata["decision"], 0)
        by_decision[c.metadata["decision"]] += 1
        by_season.setdefault(c.metadata["season"], 0)
        by_season[c.metadata["season"]] += 1
    print(f"  decision distribution: {by_decision}")
    print(f"  season distribution: {by_season}")

    # Sample
    sample = chunks[0]
    print()
    print(f"Sample chunk:")
    print(f"  id: {sample.id}")
    print(f"  metadata: {sample.metadata}")
    print(f"  document (first 400 chars):")
    print(sample.document[:400])


if __name__ == "__main__":
    main()
