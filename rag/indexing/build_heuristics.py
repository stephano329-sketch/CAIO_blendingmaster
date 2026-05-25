"""
Build Dataset E-seed (interview_seeds.json) into RAG chunks for the secondary collection.

For each interview seed, produces a single chunk centered on the veteran's
`rule_summary` — the codified tacit knowledge. Includes context, decoded
codes, and the AI draft / veteran final pattern for demo purposes.
"""

from __future__ import annotations

import json
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
SEEDS_PATH = PROJECT_ROOT / "data" / "synthetic" / "interview_seeds.json"


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


def _draft_pattern_text(pattern: str) -> str:
    return {
        "match": "Agent 초안과 베테랑 판단 일치",
        "under": "Agent 초안이 베테랑보다 낙관 (베테랑이 더 보수적)",
        "over":  "Agent 초안이 베테랑보다 과민 (베테랑이 안전 마진 정확히 봄)",
    }.get(pattern, pattern)


def _build_document_text(seed: Dict) -> str:
    """Compose RAG-friendly Korean text from seed JSON.

    Emphasis on `rule_summary` since this collection is the "암묵지" layer.
    """
    ctx = seed["context"]
    metrics = ctx["key_metrics"]
    decision = seed["decision"]
    decision_ko = decode_decision(decision)
    draft_decision = seed["ai_draft_decision"]
    draft_decision_ko = decode_decision(draft_decision)
    season_ko = _format_season(ctx["season"])
    reasons_ko = decode_reasons(seed["reason_codes"])
    checks_ko = decode_checks(seed["check_priority"])
    risks_ko = decode_risks(seed["risk_codes"])

    margin = ctx["target_cfpp"] - metrics["cfpp_measured"]

    lines = [
        f"[암묵지 {seed['case_id']}] — {season_ko}, 베테랑 판단 {decision_ko}",
        "",
        f"한 줄 기준: {seed['rule_summary']}",
        "",
        f"케이스 컨텍스트:",
        f"  - 반제품 구성: {_format_blend(ctx['blend_components'])}",
        f"  - 측정 CFPP {metrics['cfpp_measured']:.1f}°C, "
        f"목표 CFPP {ctx['target_cfpp']:.1f}°C (마진 {margin:+.1f}°C)",
        f"  - n-파라핀 C16-20 {metrics['n_paraffin_c16_c20']:.1f}wt%, "
        f"C21+ {metrics['n_paraffin_c21_plus']:.2f}wt%",
        f"  - 첨가제: {metrics['wafi_type']} 타입 {metrics['wafi_ppm']:.0f}ppm",
        f"  - 탱크 이력: {ctx['tank_history_flag']}",
        "",
        f"베테랑 판단: {decision_ko} ({decision})",
        f"판단 근거: {', '.join(reasons_ko) if reasons_ko else '없음'} "
        f"[{', '.join(seed['reason_codes'])}]",
        f"확인 우선순위: {' → '.join(checks_ko) if checks_ko else '없음'} "
        f"[{', '.join(seed['check_priority'])}]",
        f"리스크 포인트: {', '.join(risks_ko) if risks_ko else '없음'} "
        f"[{', '.join(seed['risk_codes']) if seed['risk_codes'] else '없음'}]",
        "",
        f"Agent 초안: {draft_decision_ko} ({draft_decision})",
        f"초안 vs 정답 패턴: {_draft_pattern_text(seed['draft_pattern'])} "
        f"[{seed['draft_pattern']}]",
    ]
    return "\n".join(lines)


def _build_metadata(seed: Dict) -> Dict[str, str]:
    ctx = seed["context"]
    return {
        "doc_type":           "heuristic",
        "lang":               "ko",
        "version":            "1.0",
        "source":             "synthetic",
        "case_id":            seed["case_id"],
        "season":             ctx["season"],
        "decision":           seed["decision"],
        "ai_draft_decision":  seed["ai_draft_decision"],
        "draft_pattern":      seed["draft_pattern"],
        "reason_codes":       ",".join(seed["reason_codes"]),
        "check_priority":     ",".join(seed["check_priority"]),
        "risk_codes":         ",".join(seed["risk_codes"]),
        "source_f_index":     int(seed["source_f_index"]),
        "wafi_type":          str(ctx["key_metrics"]["wafi_type"]),
    }


def build_heuristic_chunks() -> List[Chunk]:
    if not SEEDS_PATH.exists():
        raise FileNotFoundError(
            f"{SEEDS_PATH} not found. Run ml/data_generation/seed_renderer.py first."
        )
    with open(SEEDS_PATH, encoding="utf-8") as f:
        seeds = json.load(f)

    chunks: List[Chunk] = []
    for seed in seeds:
        chunk = Chunk(
            id=f"heuristic:{seed['case_id']}",
            document=_build_document_text(seed),
            metadata=_build_metadata(seed),
        )
        chunks.append(chunk)
    return chunks


def main() -> None:
    chunks = build_heuristic_chunks()
    print(f"Built {len(chunks)} heuristic chunks")

    by_decision: Dict[str, int] = {}
    by_pattern: Dict[str, int] = {}
    for c in chunks:
        by_decision.setdefault(c.metadata["decision"], 0)
        by_decision[c.metadata["decision"]] += 1
        by_pattern.setdefault(c.metadata["draft_pattern"], 0)
        by_pattern[c.metadata["draft_pattern"]] += 1
    print(f"  decision distribution: {by_decision}")
    print(f"  draft_pattern distribution: {by_pattern}")

    sample = next(c for c in chunks if c.metadata["draft_pattern"] == "under")
    print()
    print(f"Sample 'under' (낙관) chunk:")
    print(f"  id: {sample.id}")
    print(f"  metadata.draft_pattern: {sample.metadata['draft_pattern']}")
    print(f"  metadata.ai_draft_decision: {sample.metadata['ai_draft_decision']}")
    print(f"  metadata.decision: {sample.metadata['decision']}")
    print(f"  document (first 400 chars):")
    print(sample.document[:400])


if __name__ == "__main__":
    main()
