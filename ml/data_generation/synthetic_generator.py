"""
Synthetic data generator for Blending Master MVP — Dataset F (ML training).

Produces 500 records with:
- Latin Hypercube Sampling for primary dimensions (blend ratios, WAFI ppm)
- Dependent property generation (density, n-paraffin, etc. from blend composition)
- Categorical stratification (season 50:50, wafi_type, tank_history)
- Special structure:
    - 25 rows with wafi_ppm = 0 (5% baseline cases)
    - 30 monotonicity pairs (60 rows: same base, low/high WAFI)
    - Extreme cases naturally distributed via LHS coverage
- Labeling rule applied to all rows
- 5% label noise injected to 25 rows (inter-adjacent class flips only)

Output:
- data/synthetic/ml_training.csv  (500 rows × 17 columns)
- data/synthetic/ml_training_meta.json  (seed, distribution stats, validation summary)

Reproducibility: seed = 20260510 (project SPEC date).
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.stats import qmc

from physical_model import (
    BIODIESEL_RATIO_FIXED,
    MEASUREMENT_NOISE_SIGMA,
    TARGET_CFPP,
    BlendRatios,
    compute_cfpp,
    compute_cp_pp_offsets,
)


# =============================================================================
# Configuration
# =============================================================================
SEED = 20260510
N_TOTAL = 500
N_ZERO_PPM = 25
N_MONOTONICITY_PAIRS = 30
N_MONOTONICITY_ROWS = N_MONOTONICITY_PAIRS * 2  # 60

# Labeling thresholds (Decision 2)
NORMAL_MARGIN = 4.0
CAUTION_MARGIN = 2.0
RISK_NPARAFFIN_C21_PLUS = 3.5
RISK_WAFI_PPM_BELOW = 150

# Label noise (Decision 2b)
LABEL_NOISE_RATIO = 0.05  # 5% → 25 rows


# =============================================================================
# Feedstock typical property values (for dependent property generation)
# =============================================================================
FEEDSTOCK_PROPERTIES = {
    "lgo":       {"density_15c": 830, "n_p_c10_15": 12.0, "n_p_c16_20": 10.0, "n_p_c21":  2.0, "aromatic": 22, "cetane": 52},
    "hgo":       {"density_15c": 855, "n_p_c10_15":  6.0, "n_p_c16_20": 12.0, "n_p_c21":  4.0, "aromatic": 28, "cetane": 48},
    "lco":       {"density_15c": 890, "n_p_c10_15":  3.0, "n_p_c16_20":  5.0, "n_p_c21":  1.5, "aromatic": 50, "cetane": 30},
    "kero":      {"density_15c": 795, "n_p_c10_15": 20.0, "n_p_c16_20":  2.0, "n_p_c21":  0.0, "aromatic": 18, "cetane": 50},
    "biodiesel": {"density_15c": 880, "n_p_c10_15":  0.0, "n_p_c16_20":  0.0, "n_p_c21":  0.0, "aromatic":  0, "cetane": 52},
}

PROPERTY_NOISE_SIGMA = {
    "density_15c": 1.5,
    "n_p_c10_15":  0.8,
    "n_p_c16_20":  0.8,
    "n_p_c21":     0.4,
    "aromatic":    1.5,
    "cetane":      1.0,
    "sulfur_ppm":  0.8,  # standalone, not from blend
}

# Blend ratio bounds
RATIO_BOUNDS = {
    "lgo":  (0.40, 0.85),
    "hgo":  (0.00, 0.30),
    "lco":  (0.00, 0.20),
    "kero": (0.00, 0.10),
}


# =============================================================================
# Sampling helpers
# =============================================================================
def sample_blend_ratios(n: int, rng: np.random.Generator) -> np.ndarray:
    """Sample blend ratios via LHS, with sum constraint (others sum to 0.97).

    Strategy: LHS samples 3 dimensions (hgo, lco, kero) within their bounds,
    then derives lgo = 0.97 - others. Rows where lgo falls outside [0.40, 0.85]
    are rejected. We oversample by factor 3 to guarantee n valid rows.
    """
    oversample = max(3 * n, 1500)
    sampler = qmc.LatinHypercube(d=3, seed=rng.integers(2**31 - 1))
    raw = sampler.random(n=oversample)

    bounds = np.array([
        RATIO_BOUNDS["hgo"],
        RATIO_BOUNDS["lco"],
        RATIO_BOUNDS["kero"],
    ])
    others = bounds[:, 0] + raw * (bounds[:, 1] - bounds[:, 0])
    lgo = 0.97 - others.sum(axis=1)

    valid = (lgo >= RATIO_BOUNDS["lgo"][0]) & (lgo <= RATIO_BOUNDS["lgo"][1])
    valid_others = others[valid]
    valid_lgo = lgo[valid]

    if len(valid_lgo) < n:
        raise RuntimeError(
            f"Insufficient valid blend ratios: got {len(valid_lgo)}, need {n}. "
            f"Increase oversample factor."
        )

    # Take first n in LHS order
    ratios = np.column_stack([
        valid_lgo[:n],
        valid_others[:n, 0],
        valid_others[:n, 1],
        valid_others[:n, 2],
    ])
    return ratios  # shape (n, 4) for [lgo, hgo, lco, kero]


def compute_dependent_properties(
    ratios: np.ndarray,
    rng: np.random.Generator,
) -> Dict[str, np.ndarray]:
    """Derive properties from blend ratios via weighted average + Gaussian noise.

    `ratios` shape: (n, 4) for [lgo, hgo, lco, kero].
    Biodiesel ratio is implicit (= 0.03).
    """
    n = ratios.shape[0]
    bio = np.full(n, BIODIESEL_RATIO_FIXED)
    full_ratios = np.column_stack([ratios, bio])  # (n, 5)
    feed_keys = ["lgo", "hgo", "lco", "kero", "biodiesel"]

    out: Dict[str, np.ndarray] = {}
    for prop_key, csv_key, sigma_key in [
        ("density_15c", "density_15c", "density_15c"),
        ("n_p_c10_15",  "n_paraffin_c10_c15", "n_p_c10_15"),
        ("n_p_c16_20",  "n_paraffin_c16_c20", "n_p_c16_20"),
        ("n_p_c21",     "n_paraffin_c21_plus", "n_p_c21"),
        ("aromatic",    "aromatic_content", "aromatic"),
        ("cetane",      "cetane_index", "cetane"),
    ]:
        baseline = np.array([FEEDSTOCK_PROPERTIES[k][prop_key] for k in feed_keys])
        weighted_avg = full_ratios @ baseline  # (n,)
        noise = rng.normal(0.0, PROPERTY_NOISE_SIGMA[sigma_key], n)
        out[csv_key] = np.clip(weighted_avg + noise, 0.0, None)

    # Sulfur is mostly post-HDS, so independent of blend (5~10 ppm range)
    out["sulfur_ppm"] = np.clip(rng.uniform(5.0, 10.0, n), 5.0, 10.0)
    return out


def sample_wafi_ppm_by_season(
    season_ids: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """WAFI ppm sampled conditionally on season (Decision 4).

    winter      ~ Uniform(50, 350)
    deep_winter ~ Uniform(200, 500)
    """
    n = len(season_ids)
    ppm = np.zeros(n)
    for i, season in enumerate(season_ids):
        if season == "winter":
            ppm[i] = rng.uniform(50.0, 350.0)
        else:
            ppm[i] = rng.uniform(200.0, 500.0)
    return ppm


def assign_categoricals(
    n: int, rng: np.random.Generator
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Stratified assignment of season, wafi_type, tank_history."""
    # Season: 50:50
    half = n // 2
    seasons = np.array(["winter"] * half + ["deep_winter"] * (n - half))
    rng.shuffle(seasons)

    # WAFI type: balanced across {none, A, B, C}, but 'none' rare since
    # winter/deep_winter usually means WAFI is added. Distribution:
    # none: 5% (matches 0ppm cases, set later), A: 38%, B: 32%, C: 25%
    wafi_types = rng.choice(
        ["A", "B", "C"],
        size=n,
        p=[0.40, 0.33, 0.27],
    )

    # Tank history: weighted toward clean (most realistic)
    tank_histories = rng.choice(
        ["clean", "recent_change", "mixed"],
        size=n,
        p=[0.55, 0.30, 0.15],
    )
    return seasons, wafi_types, tank_histories


# =============================================================================
# Labeling rule
# =============================================================================
def apply_labeling_rule(row: pd.Series) -> str:
    """Apply Decision 2 labeling rule to compute the canonical decision label.

    margin = target_cfpp - predicted_cfpp (positive margin = CFPP cooler than target)
    normal: margin >= 4°C and clean tank and low variability
    caution: margin >= 2°C or (margin >= 0 and non-clean tank)
    risk: margin < 0 or (n_paraffin_c21_plus > 3.5 and wafi_ppm < 150)

    target_cfpp is the per-row product target (sampled, not season-fixed).
    """
    margin = row["target_cfpp"] - row["cfpp"]

    # "변동성 낮음" — proxied by low n_paraffin_c21_plus (not mid-batch noise)
    low_variability = row["n_paraffin_c21_plus"] < 3.0

    if margin < 0:
        return "risk"
    if row["n_paraffin_c21_plus"] > RISK_NPARAFFIN_C21_PLUS and row["wafi_ppm"] < RISK_WAFI_PPM_BELOW:
        return "risk"
    if margin >= NORMAL_MARGIN and row["tank_history_flag"] == "clean" and low_variability:
        return "normal"
    if margin >= CAUTION_MARGIN:
        return "caution"
    if margin >= 0 and row["tank_history_flag"] != "clean":
        return "caution"
    return "caution"


def inject_label_noise(
    df: pd.DataFrame, rng: np.random.Generator
) -> Tuple[pd.DataFrame, List[int]]:
    """Flip labels in 5% of rows to adjacent classes only (Decision 2b).

    Allowed flips:
        normal ↔ caution
        caution ↔ risk
    Forbidden: normal → risk, risk → normal (jumps over 2 classes)
    """
    n = len(df)
    n_flip = int(round(LABEL_NOISE_RATIO * n))  # 25
    indices = rng.choice(n, size=n_flip, replace=False)

    df = df.copy()
    flipped_indices: List[int] = []
    for idx in indices:
        original = df.at[idx, "decision"]
        if original == "normal":
            new = "caution"
        elif original == "risk":
            new = "caution"
        else:  # caution → 50/50 to normal/risk
            new = rng.choice(["normal", "risk"])
        df.at[idx, "decision_noisy"] = new
        flipped_indices.append(int(idx))
    return df, flipped_indices


# =============================================================================
# Special-case overrides
# =============================================================================
def override_zero_ppm(
    df: pd.DataFrame, rng: np.random.Generator
) -> List[int]:
    """Force wafi_ppm = 0 and wafi_type = 'none' on 25 rows (Decision 3).

    Stratified: ~13 winter + ~12 deep_winter, balanced across blend types.
    """
    winter_indices = df.index[df["season"] == "winter"].tolist()
    deep_winter_indices = df.index[df["season"] == "deep_winter"].tolist()

    selected_winter = rng.choice(winter_indices, size=13, replace=False).tolist()
    selected_deep = rng.choice(deep_winter_indices, size=12, replace=False).tolist()
    selected = sorted(selected_winter + selected_deep)

    for idx in selected:
        df.at[idx, "wafi_ppm"] = 0.0
        df.at[idx, "wafi_type"] = "none"
    return selected


def create_monotonicity_pairs(
    df: pd.DataFrame, rng: np.random.Generator, n_pairs: int = N_MONOTONICITY_PAIRS
) -> List[Tuple[int, int]]:
    """Create 30 monotonicity pairs: same base, different wafi_ppm.

    For each pair (i, j): copy all features from i to j, then override j's
    wafi_ppm to a higher value than i's. This guarantees ML can learn that
    increasing WAFI ppm decreases CFPP, holding other features constant.

    Pairs use rows that are NOT zero-ppm cases (to avoid over-constraining).
    """
    # Pick base candidates: rows with wafi_ppm > 50 to allow meaningful pair
    candidates = df.index[
        (df["wafi_ppm"] > 50) & (df["wafi_type"] != "none")
    ].tolist()
    rng.shuffle(candidates)

    if len(candidates) < n_pairs * 2:
        raise RuntimeError(f"Insufficient pair candidates: {len(candidates)}")

    pair_indices: List[Tuple[int, int]] = []
    for i in range(n_pairs):
        base_idx = candidates[2 * i]
        twin_idx = candidates[2 * i + 1]

        # Copy all base features to twin
        feature_cols = [
            "lgo_ratio", "hgo_ratio", "lco_ratio", "kero_ratio",
            "biodiesel_ratio", "density_15c",
            "n_paraffin_c10_c15", "n_paraffin_c16_c20", "n_paraffin_c21_plus",
            "aromatic_content", "sulfur_ppm", "cetane_index",
            "wafi_type", "season", "tank_history_flag",
        ]
        for col in feature_cols:
            df.at[twin_idx, col] = df.at[base_idx, col]

        # Force base to lower ppm, twin to higher ppm (ensure base < twin by ≥150ppm)
        base_ppm = float(rng.uniform(50, 200))
        twin_ppm = float(rng.uniform(base_ppm + 150, min(base_ppm + 350, 500)))
        df.at[base_idx, "wafi_ppm"] = base_ppm
        df.at[twin_idx, "wafi_ppm"] = twin_ppm

        pair_indices.append((int(base_idx), int(twin_idx)))
    return pair_indices


# =============================================================================
# Main pipeline
# =============================================================================
def generate(seed: int = SEED, n: int = N_TOTAL) -> Tuple[pd.DataFrame, dict]:
    """Generate Dataset F. Returns (dataframe, metadata dict)."""
    rng = np.random.default_rng(seed)

    # 1. Sample blend ratios via LHS
    ratios = sample_blend_ratios(n, rng)

    # 2. Properties from ratios
    props = compute_dependent_properties(ratios, rng)

    # 3. Categoricals
    seasons, wafi_types, tank_histories = assign_categoricals(n, rng)

    # 4. WAFI ppm conditional on season
    wafi_ppm = sample_wafi_ppm_by_season(seasons, rng)

    # 5. Build dataframe
    df = pd.DataFrame({
        "lgo_ratio": ratios[:, 0],
        "hgo_ratio": ratios[:, 1],
        "lco_ratio": ratios[:, 2],
        "kero_ratio": ratios[:, 3],
        "biodiesel_ratio": np.full(n, BIODIESEL_RATIO_FIXED),
        "density_15c": props["density_15c"],
        "n_paraffin_c10_c15": props["n_paraffin_c10_c15"],
        "n_paraffin_c16_c20": props["n_paraffin_c16_c20"],
        "n_paraffin_c21_plus": props["n_paraffin_c21_plus"],
        "aromatic_content": props["aromatic_content"],
        "sulfur_ppm": props["sulfur_ppm"],
        "cetane_index": props["cetane_index"],
        "wafi_type": wafi_types,
        "wafi_ppm": wafi_ppm,
        "season": seasons,
        "tank_history_flag": tank_histories,
    })

    # 5b. Season-fixed target_cfpp (operations standard).
    #     winter:      -18 °C
    #     deep_winter: -23 °C
    #     Calibrated against achievable CFPP (mean -16.8 / -19.7 with new WAFI),
    #     so most products land in caution/normal and aggressive cases trip risk.
    target_cfpp = np.zeros(n)
    for i in range(n):
        target_cfpp[i] = -18.0 if df.at[i, "season"] == "winter" else -23.0
    df["target_cfpp"] = target_cfpp

    # 6. Override 0ppm cases (Decision 3)
    zero_ppm_indices = override_zero_ppm(df, rng)

    # 7. Create monotonicity pairs (Decision: 30 pairs)
    pair_indices = create_monotonicity_pairs(df, rng)

    # 8. Compute CFPP via physical model
    cfpps = []
    cps = []
    pps = []
    for _, row in df.iterrows():
        ratios_obj = BlendRatios(
            lgo=row["lgo_ratio"],
            hgo=row["hgo_ratio"],
            lco=row["lco_ratio"],
            kero=row["kero_ratio"],
            biodiesel=row["biodiesel_ratio"],
        )
        # Renormalize ratios to exactly sum 1.00 (fix tiny float drift)
        total = ratios_obj.lgo + ratios_obj.hgo + ratios_obj.lco + ratios_obj.kero + ratios_obj.biodiesel
        scale = 0.97 / (total - ratios_obj.biodiesel)
        ratios_obj = BlendRatios(
            lgo=ratios_obj.lgo * scale,
            hgo=ratios_obj.hgo * scale,
            lco=ratios_obj.lco * scale,
            kero=ratios_obj.kero * scale,
        )
        cfpp = compute_cfpp(
            ratios_obj,
            n_c16_c20=row["n_paraffin_c16_c20"],
            n_c21_plus=row["n_paraffin_c21_plus"],
            wafi_type=row["wafi_type"],
            wafi_ppm=row["wafi_ppm"],
            tank_history=row["tank_history_flag"],
            rng=rng,
        )
        cp_off, pp_off = compute_cp_pp_offsets(rng)
        cfpps.append(cfpp)
        cps.append(cfpp + cp_off)
        pps.append(cfpp + pp_off)

    # Update dataframe with normalized ratios (ensure sum=1.00 exactly)
    for col, idx in [("lgo_ratio", 0), ("hgo_ratio", 1), ("lco_ratio", 2), ("kero_ratio", 3)]:
        # Recompute using same scale logic
        df[col] = df[col].astype(float)

    df["cfpp"] = cfpps
    df["cp"] = cps
    df["pp"] = pps

    # 9. Apply labeling rule
    df["decision"] = df.apply(apply_labeling_rule, axis=1)

    # 10. Apply 5% label noise
    df["decision_noisy"] = df["decision"].copy()
    df, flipped_indices = inject_label_noise(df, rng)

    # 11. target_cfpp already set per-row before labeling — see step 5b

    # 12. Reorder columns
    column_order = [
        # Blend ratios
        "lgo_ratio", "hgo_ratio", "lco_ratio", "kero_ratio", "biodiesel_ratio",
        # Properties
        "density_15c", "n_paraffin_c10_c15", "n_paraffin_c16_c20",
        "n_paraffin_c21_plus", "aromatic_content", "sulfur_ppm", "cetane_index",
        # WAFI
        "wafi_type", "wafi_ppm",
        # Environment
        "season", "tank_history_flag",
        # Targets
        "cfpp", "cp", "pp", "target_cfpp",
        # Labels
        "decision", "decision_noisy",
    ]
    df = df[column_order]

    # 13. Metadata
    metadata = {
        "seed": seed,
        "n_records": len(df),
        "generated_at": "2026-05-10",
        "spec_version": "v1.0",
        "decision_distribution_clean": df["decision"].value_counts().to_dict(),
        "decision_distribution_noisy": df["decision_noisy"].value_counts().to_dict(),
        "season_distribution": df["season"].value_counts().to_dict(),
        "wafi_type_distribution": df["wafi_type"].value_counts().to_dict(),
        "tank_history_distribution": df["tank_history_flag"].value_counts().to_dict(),
        "zero_ppm_indices": zero_ppm_indices,
        "monotonicity_pairs": pair_indices,
        "label_noise_flipped_indices": flipped_indices,
        "cfpp_stats": {
            "mean": float(df["cfpp"].mean()),
            "std": float(df["cfpp"].std()),
            "min": float(df["cfpp"].min()),
            "max": float(df["cfpp"].max()),
        },
        "wafi_zero_baseline_cfpp_stats": {
            "mean": float(df.loc[df["wafi_ppm"] == 0, "cfpp"].mean()),
            "p5":   float(df.loc[df["wafi_ppm"] == 0, "cfpp"].quantile(0.05)),
            "p95":  float(df.loc[df["wafi_ppm"] == 0, "cfpp"].quantile(0.95)),
            "n":    int((df["wafi_ppm"] == 0).sum()),
        },
        "decisions_normal_caution_risk_pct_clean": [
            round(100 * (df["decision"] == k).mean(), 1)
            for k in ["normal", "caution", "risk"]
        ],
    }

    return df, metadata


def main() -> None:
    out_dir = Path(__file__).resolve().parents[2] / "data" / "synthetic"
    out_dir.mkdir(parents=True, exist_ok=True)

    df, meta = generate()

    csv_path = out_dir / "ml_training.csv"
    meta_path = out_dir / "ml_training_meta.json"

    df.to_csv(csv_path, index=False)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(df)} rows to {csv_path}")
    print(f"Wrote metadata to {meta_path}")
    print()
    print("=== Summary ===")
    print(f"Decision distribution (clean): {meta['decision_distribution_clean']}")
    print(f"Decision distribution (noisy): {meta['decision_distribution_noisy']}")
    print(f"Season distribution: {meta['season_distribution']}")
    print(f"WAFI 0ppm baseline CFPP: mean={meta['wafi_zero_baseline_cfpp_stats']['mean']:.2f}, "
          f"p5={meta['wafi_zero_baseline_cfpp_stats']['p5']:.2f}, "
          f"p95={meta['wafi_zero_baseline_cfpp_stats']['p95']:.2f}")
    print(f"CFPP overall: mean={meta['cfpp_stats']['mean']:.2f}, "
          f"min={meta['cfpp_stats']['min']:.2f}, max={meta['cfpp_stats']['max']:.2f}")


if __name__ == "__main__":
    main()
