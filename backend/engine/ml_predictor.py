"""XGBoost CFPP predictor wrapper.

Loads the trained pipeline (pre-processor + XGBoost regressor) from disk.
Falls back to a heuristic estimator if the model file is missing, so the
API can still respond during initial setup.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

MODEL_PATH = Path(__file__).resolve().parents[2] / "ml" / "models" / "cfpp_xgb_v1.pkl"

FEATURE_COLUMNS = [
    "lgo_ratio",
    "hgo_ratio",
    "lco_ratio",
    "kero_ratio",
    "biodiesel_ratio",
    "density_15c",
    "n_paraffin_c10_c15",
    "n_paraffin_c16_c20",
    "n_paraffin_c21_plus",
    "aromatic_content",
    "sulfur_ppm",
    "cetane_index",
    "wafi_type",
    "wafi_ppm",
    "season",
    "tank_history_flag",
]


class CfppPredictor:
    """Thin wrapper around the trained model with a heuristic fallback."""

    def __init__(self, model_path: Path = MODEL_PATH) -> None:
        self.model_path = model_path
        self._pipeline: Any | None = None
        self._load()

    def _load(self) -> None:
        if self.model_path.exists():
            self._pipeline = joblib.load(self.model_path)
        else:
            self._pipeline = None

    @property
    def is_loaded(self) -> bool:
        return self._pipeline is not None

    def predict(self, features: dict) -> float:
        """Predict CFPP (degrees Celsius) for a single input dict."""
        if self._pipeline is None:
            return self._heuristic_fallback(features)

        row = {col: features.get(col) for col in FEATURE_COLUMNS}
        df = pd.DataFrame([row], columns=FEATURE_COLUMNS)
        pred = self._pipeline.predict(df)
        return float(pred[0])

    def predict_with_wafi_sweep(
        self,
        base_features: dict,
        wafi_ppm_grid: list[float],
        wafi_type: str = "A",
    ) -> list[tuple[float, float]]:
        """Return list of (wafi_ppm, predicted_cfpp) for the given grid."""
        results = []
        for ppm in wafi_ppm_grid:
            f = dict(base_features)
            f["wafi_type"] = wafi_type
            f["wafi_ppm"] = ppm
            results.append((ppm, self.predict(f)))
        return results

    @staticmethod
    def _heuristic_fallback(features: dict) -> float:
        """Crude estimator used when the trained model is unavailable.

        Calibrated against ml_training_meta.json wafi_zero_baseline_cfpp_stats
        (mean -3.6 degC) and the observed WAFI effect (~-0.025 degC per ppm).
        """
        baseline = -3.6
        ppm = float(features.get("wafi_ppm") or 0.0)
        wafi_eff = -0.025 * ppm
        season_eff = -2.0 if features.get("season") == "deep_winter" else 0.0
        c21 = float(features.get("n_paraffin_c21_plus") or 0.0)
        paraffin_eff = 0.8 * (c21 - 2.0)
        return baseline + wafi_eff + season_eff + paraffin_eff


_predictor: CfppPredictor | None = None


def get_predictor() -> CfppPredictor:
    global _predictor
    if _predictor is None:
        _predictor = CfppPredictor()
    return _predictor
