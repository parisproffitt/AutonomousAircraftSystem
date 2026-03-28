from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


@dataclass(frozen=True)
class MLConfig:
    train_window_s: int = 60          # train on first N seconds (assumed nominal)
    contamination: float = 0.03       # expected anomaly proportion
    n_estimators: int = 200
    random_state: int = 7

    # Risk threshold used ONLY for escalation/attention, not direct actuation
    risk_threshold: float = 0.65


def _build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert telemetry into a compact feature set suitable for anomaly scoring.
    Keep features interpretable and engineering-reasonable.
    """
    feats = pd.DataFrame(index=df.index)

    feats["airspeed_true"] = df["airspeed_true"]
    feats["airspeed_meas"] = df["airspeed_meas"]
    feats["airspeed_err"] = df["airspeed_err"]
    feats["vs_fpm"] = df["vs_fpm"]
    feats["pitch_deg"] = df["pitch_deg"]
    feats["roll_abs"] = df["roll_abs"]
    feats["control_effectiveness"] = df["control_effectiveness"]
    feats["turbulence"] = df["turbulence"]

    # Trend features (rolling windows)
    # Use small windows because dt=1s in v0.1
    feats["airspeed_true_d1"] = df["airspeed_true"].diff().fillna(0.0)
    feats["altitude_d1"] = df["altitude_ft"].diff().fillna(0.0)

    # Rolling variability proxies (turbulence / instability)
    feats["roll_std_10"] = df["roll_deg"].rolling(10, min_periods=1).std().fillna(0.0)
    feats["airspeed_err_std_10"] = df["airspeed_err"].rolling(10, min_periods=1).std().fillna(0.0)

    # Fill any residual NaNs defensively
    return feats.replace([np.inf, -np.inf], np.nan).fillna(0.0)


def score_anomaly_risk(df: pd.DataFrame, cfg: MLConfig) -> Tuple[pd.Series, IsolationForest]:
    """
    Returns:
      - risk score in [0..1] where higher = more anomalous
      - fitted IsolationForest model

    Training strategy:
      - Fit on first `train_window_s` seconds (assumed nominal)
      - Score the full mission
    """
    feats = _build_features(df)

    # Training slice: first N seconds (by time column if present)
    if "t" in df.columns:
        train_mask = df["t"] <= float(cfg.train_window_s)
    else:
        train_mask = np.arange(len(df)) < int(cfg.train_window_s)

    X_train = feats.loc[train_mask].to_numpy(dtype=float)
    X_all = feats.to_numpy(dtype=float)

    model = IsolationForest(
        n_estimators=cfg.n_estimators,
        contamination=cfg.contamination,
        random_state=cfg.random_state,
    )
    model.fit(X_train)

    # IsolationForest decision_function: higher = more normal
    normality = model.decision_function(X_all)

    # Convert to risk score [0..1] where 1 = most anomalous
    # Normalize using mission min/max to make it visually stable for demos
    norm_min = float(np.min(normality))
    norm_max = float(np.max(normality))
    if abs(norm_max - norm_min) < 1e-9:
        risk = np.zeros_like(normality)
    else:
        risk = (norm_max - normality) / (norm_max - norm_min)

    risk_series = pd.Series(risk, index=df.index, name="ml_risk")
    return risk_series, model