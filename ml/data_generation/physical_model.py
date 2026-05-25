"""
Physical model for CFPP (Cold Filter Plugging Point) prediction in diesel blending.

Implements:
- Kay's Mixing Rule for baseline CFPP from feedstock weighted average
- n-paraffin distribution adjustment (C16-C20, C21+)
- WAFI (Wax Anti-settling Flow Improver) response curve with type-specific saturation
- LCO content damping effect on WAFI
- Tank history offset
- Measurement noise

All parameters come from `.moai/plans/prd-snug-orbit.md` (Decisions 1, 1b).
PRD reference: `Blending_Master_PRD_v2_3.md` Appendix B.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Optional, Tuple

import numpy as np


WafiType = Literal["A", "B", "C", "none"]
TankHistory = Literal["clean", "recent_change", "mixed"]
Season = Literal["winter", "deep_winter"]


# =============================================================================
# Baseline CFPP per feedstock (°C) — Decision 1 calibration
# Calibrated so that WAFI 0ppm cases produce CFPP_base ∈ [-10, +5]°C
# =============================================================================
FEEDSTOCK_CFPP_BASELINE = {
    "lgo": -6.0,
    "hgo": +4.0,
    "lco": -6.0,
    "kero": -40.0,
    "biodiesel": +5.0,
}

# Biodiesel ratio is fixed by Korean diesel spec
BIODIESEL_RATIO_FIXED = 0.03


# =============================================================================
# WAFI response curve parameters — Decision 1 (Option ①, Standard)
# ΔCFPP = -A × (1 - exp(-k × ppm))
# Type A: balanced  | Type B: low-ppm efficient | Type C: high-ppm potential
# =============================================================================
WAFI_RESPONSE = {
    "A":    {"A_max": 18.0, "k": 0.008},
    "B":    {"A_max": 23.0, "k": 0.010},
    "C":    {"A_max": 25.0, "k": 0.005},
    "none": {"A_max":  0.0, "k": 0.000},
}

# LCO damping rule (Decision 1b): lco_ratio > 0.15 attenuates WAFI by 30%
LCO_DAMPING_THRESHOLD = 0.15
LCO_DAMPING_FACTOR = 0.70


# =============================================================================
# n-paraffin distribution adjustment
# δ_nparaffin = β1 × (n_C16_C20 - μ_C16_C20) + β2 × (n_C21_plus - μ_C21_plus)
# Range expected: [-3, +4]°C
# =============================================================================
NPARAFFIN_C16_C20_MEAN = 9.0
NPARAFFIN_C21_PLUS_MEAN = 2.0
NPARAFFIN_C16_C20_BETA = 0.7
NPARAFFIN_C21_PLUS_BETA = 1.4


# =============================================================================
# Tank history offset (°C)
# =============================================================================
TANK_HISTORY_OFFSET = {
    "clean": 0.0,
    "recent_change": +1.0,
    "mixed": +2.0,
}


# =============================================================================
# Measurement noise (°C, 1σ)
# =============================================================================
MEASUREMENT_NOISE_SIGMA = 0.8


# =============================================================================
# Seasonal target CFPP (Korean diesel spec)
# =============================================================================
TARGET_CFPP = {
    "winter": -16.0,
    "deep_winter": -23.0,
}


@dataclass
class BlendRatios:
    """Feedstock blend ratios. Sum must equal 1.00 (within tolerance).

    Biodiesel is fixed at 0.03 by Korean diesel spec; the remaining four
    feedstocks must sum to 0.97.
    """

    lgo: float
    hgo: float
    lco: float
    kero: float
    biodiesel: float = BIODIESEL_RATIO_FIXED

    def validate(self, tol: float = 1e-3) -> None:
        total = self.lgo + self.hgo + self.lco + self.kero + self.biodiesel
        if abs(total - 1.0) > tol:
            raise ValueError(f"Blend ratios must sum to 1.00, got {total:.6f}")
        if abs(self.biodiesel - BIODIESEL_RATIO_FIXED) > tol:
            raise ValueError(
                f"biodiesel must be fixed at {BIODIESEL_RATIO_FIXED}, "
                f"got {self.biodiesel:.6f}"
            )
        for name, value in [
            ("lgo", self.lgo), ("hgo", self.hgo),
            ("lco", self.lco), ("kero", self.kero),
        ]:
            if value < 0.0:
                raise ValueError(f"{name} ratio must be non-negative, got {value}")


def compute_baseline_cfpp(ratios: BlendRatios) -> float:
    """Kay's Mixing Rule: weighted average of feedstock baseline CFPP."""
    return (
        ratios.lgo * FEEDSTOCK_CFPP_BASELINE["lgo"]
        + ratios.hgo * FEEDSTOCK_CFPP_BASELINE["hgo"]
        + ratios.lco * FEEDSTOCK_CFPP_BASELINE["lco"]
        + ratios.kero * FEEDSTOCK_CFPP_BASELINE["kero"]
        + ratios.biodiesel * FEEDSTOCK_CFPP_BASELINE["biodiesel"]
    )


def compute_nparaffin_delta(n_c16_c20: float, n_c21_plus: float) -> float:
    """n-paraffin distribution adjustment to CFPP base."""
    return (
        NPARAFFIN_C16_C20_BETA * (n_c16_c20 - NPARAFFIN_C16_C20_MEAN)
        + NPARAFFIN_C21_PLUS_BETA * (n_c21_plus - NPARAFFIN_C21_PLUS_MEAN)
    )


def compute_wafi_effect(
    wafi_type: WafiType,
    wafi_ppm: float,
    lco_ratio: float,
) -> float:
    """WAFI response curve: ΔCFPP = -A × (1 - exp(-k × ppm)).

    LCO content > 15% attenuates effect by 30% (Decision 1b).

    Returns ΔCFPP (°C, negative = CFPP decreases / cold flow improves).
    """
    if wafi_ppm < 0:
        raise ValueError(f"wafi_ppm must be non-negative, got {wafi_ppm}")
    params = WAFI_RESPONSE[wafi_type]
    base_effect = -params["A_max"] * (1.0 - math.exp(-params["k"] * wafi_ppm))
    if lco_ratio > LCO_DAMPING_THRESHOLD:
        return base_effect * LCO_DAMPING_FACTOR
    return base_effect


def compute_cfpp(
    ratios: BlendRatios,
    n_c16_c20: float,
    n_c21_plus: float,
    wafi_type: WafiType,
    wafi_ppm: float,
    tank_history: TankHistory,
    rng: Optional[np.random.Generator] = None,
) -> float:
    """Full CFPP prediction pipeline.

    Order: baseline + n-paraffin delta + WAFI effect + tank offset + noise.
    """
    ratios.validate()
    base = compute_baseline_cfpp(ratios)
    delta_n = compute_nparaffin_delta(n_c16_c20, n_c21_plus)
    delta_wafi = compute_wafi_effect(wafi_type, wafi_ppm, ratios.lco)
    tank_offset = TANK_HISTORY_OFFSET[tank_history]
    noise = rng.normal(0.0, MEASUREMENT_NOISE_SIGMA) if rng is not None else 0.0
    return base + delta_n + delta_wafi + tank_offset + noise


def compute_cp_pp_offsets(
    rng: Optional[np.random.Generator] = None,
) -> Tuple[float, float]:
    """CP (Cloud Point) and PP (Pour Point) offsets relative to CFPP.

    CP = CFPP + 2~5°C  (cloud point is warmer than CFPP)
    PP = CFPP + 5~9°C  (pour point is even warmer)
    """
    if rng is None:
        return 3.5, 7.0
    return float(rng.uniform(2.0, 5.0)), float(rng.uniform(5.0, 9.0))


def compute_baseline_range_check() -> dict:
    """Sanity check: enumerate extreme cases to verify baseline distribution
    falls within [-10, +5]°C as required by user constraint.
    """
    cases = {
        "min_cfpp": BlendRatios(lgo=0.80, hgo=0.00, lco=0.07, kero=0.10),
        "median": BlendRatios(lgo=0.65, hgo=0.20, lco=0.07, kero=0.05),
        "max_cfpp": BlendRatios(lgo=0.45, hgo=0.30, lco=0.20, kero=0.02),
    }
    return {name: compute_baseline_cfpp(r) for name, r in cases.items()}


if __name__ == "__main__":
    import json
    print("Baseline CFPP extreme cases (no n-paraffin, no WAFI):")
    print(json.dumps(compute_baseline_range_check(), indent=2))
    print()
    print("WAFI response at 100/200/300/500 ppm (LCO=0%):")
    for wtype in ["A", "B", "C"]:
        line = f"  Type {wtype}:"
        for ppm in [100, 200, 300, 500]:
            line += f"  {ppm}ppm={compute_wafi_effect(wtype, ppm, 0.0):+.2f}°C"
        print(line)
