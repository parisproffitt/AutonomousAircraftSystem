"""ML risk scoring via Isolation Forest – early warning only, not actuation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from autoflight.features.engineering import build_ml_features


@dataclass(frozen=True)
class MLConfig:
    train_window_s: int = 60
    contamination: float = 0.04
    n_estimators: int = 200
    random_state: int = 7
    risk_threshold: float = 0.65


def score_anomaly_risk(df: pd.DataFrame, cfg: MLConfig) -> Tuple[pd.Series, IsolationForest]:
    """
    Fit Isolation Forest on early mission window (assumed nominal).
    Returns risk scores in [0, 1] – higher means more anomalous.
    ML provides early warning only; recovery actions use rule/policy authority.
    """
    feats = build_ml_features(df)

    if "t" in df.columns:
        train_mask = df["t"] <= float(cfg.train_window_s)
    else:
        train_mask = np.arange(len(df)) < cfg.train_window_s

    X_train = feats.loc[train_mask].to_numpy(dtype=float)
    X_all = feats.to_numpy(dtype=float)

    if len(X_train) < 10:
        X_train = X_all[: max(10, len(X_all) // 4)]

    model = IsolationForest(
        n_estimators=cfg.n_estimators,
        contamination=cfg.contamination,
        random_state=cfg.random_state,
    )
    model.fit(X_train)

    normality = model.decision_function(X_all)
    n_min, n_max = float(np.min(normality)), float(np.max(normality))

    if abs(n_max - n_min) < 1e-9:
        risk = np.zeros(len(normality))
    else:
        risk = (n_max - normality) / (n_max - n_min)

    return pd.Series(risk, index=df.index, name="ml_risk"), model
