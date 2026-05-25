"""Train XGBoost CFPP regressor on data/synthetic/ml_training.csv.

Usage:
    python -m ml.training.train_cfpp

Outputs:
    ml/models/cfpp_xgb_v1.pkl      (joblib bundle: sklearn Pipeline)
    ml/models/metrics.json         (MAE, RMSE, R^2 on holdout)
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "data" / "synthetic" / "ml_training.csv"
MODEL_DIR = PROJECT_ROOT / "ml" / "models"
MODEL_PATH = MODEL_DIR / "cfpp_xgb_v1.pkl"
METRICS_PATH = MODEL_DIR / "metrics.json"

NUMERIC_FEATURES = [
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
    "wafi_ppm",
]
CATEGORICAL_FEATURES = ["wafi_type", "season", "tank_history_flag"]
ALL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
TARGET = "cfpp"


def build_pipeline() -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_FEATURES,
            ),
        ],
        remainder="passthrough",
    )
    regressor = XGBRegressor(
        n_estimators=400,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.85,
        colsample_bytree=0.85,
        objective="reg:squarederror",
        random_state=42,
        n_jobs=-1,
    )
    return Pipeline(steps=[("pre", preprocessor), ("xgb", regressor)])


def main() -> None:
    print(f"[train] Loading {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    print(f"[train] Loaded {len(df)} records")

    X = df[ALL_FEATURES]
    y = df[TARGET].astype(float)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    pipeline = build_pipeline()
    print("[train] Fitting XGBoost pipeline...")
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    mae = float(mean_absolute_error(y_test, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
    r2 = float(r2_score(y_test, y_pred))

    print("[train] === Holdout metrics ===")
    print(f"        MAE  = {mae:.3f} °C   (target ≤ 2.0)")
    print(f"        RMSE = {rmse:.3f} °C")
    print(f"        R²   = {r2:.3f}     (target ≥ 0.85)")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    METRICS_PATH.write_text(
        json.dumps(
            {
                "model_version": "cfpp_xgb_v1",
                "n_train": int(len(X_train)),
                "n_test": int(len(X_test)),
                "mae": mae,
                "rmse": rmse,
                "r2": r2,
                "target_mae": 2.0,
                "target_r2": 0.85,
                "meets_mae_target": mae <= 2.0,
                "meets_r2_target": r2 >= 0.85,
                "features": ALL_FEATURES,
                "target": TARGET,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[train] Saved model    -> {MODEL_PATH}")
    print(f"[train] Saved metrics  -> {METRICS_PATH}")


if __name__ == "__main__":
    main()
