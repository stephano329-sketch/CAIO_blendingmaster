"""Simple similar-case retriever using numeric feature distance.

This is a placeholder for the ChromaDB-backed RAG retriever planned for
Phase 2. For Phase 1 we use scalar feature normalization + Euclidean
distance over the Case table.
"""
from __future__ import annotations

import math
from typing import Iterable

from sqlalchemy.orm import Session

from backend.models import Case

NUMERIC_KEYS = [
    "density_15c",
    "n_paraffin_c16_c20",
    "n_paraffin_c21_plus",
    "aromatic_content",
    "cetane_index",
]

# Rough feature scales for normalization (std-dev from training data)
SCALES = {
    "density_15c": 5.0,
    "n_paraffin_c16_c20": 2.0,
    "n_paraffin_c21_plus": 1.0,
    "aromatic_content": 4.0,
    "cetane_index": 3.0,
    "target_cfpp": 4.0,
    "wafi_ppm": 150.0,
}


def _normalized_distance(a: dict, b: dict) -> float:
    total = 0.0
    n = 0
    for key in NUMERIC_KEYS:
        av = a.get(key)
        bv = b.get(key)
        if av is None or bv is None:
            continue
        scale = SCALES.get(key, 1.0)
        total += ((av - bv) / scale) ** 2
        n += 1
    if n == 0:
        return math.inf
    return math.sqrt(total / n)


def find_similar_cases(
    db: Session,
    query_metrics: dict,
    target_cfpp: float,
    season: str,
    top_k: int = 3,
) -> list[tuple[Case, float]]:
    cases: Iterable[Case] = db.query(Case).filter(Case.season == season).all()
    if not cases:
        cases = db.query(Case).all()

    scored: list[tuple[Case, float]] = []
    for c in cases:
        metrics = dict(c.key_metrics or {})
        dist = _normalized_distance(query_metrics, metrics)
        cfpp_pen = abs((c.target_cfpp or 0.0) - target_cfpp) / SCALES["target_cfpp"]
        scored.append((c, dist + 0.5 * cfpp_pen))

    scored.sort(key=lambda x: x[1])
    return scored[:top_k]


def distance_to_similarity(dist: float) -> float:
    return float(1.0 / (1.0 + dist))
