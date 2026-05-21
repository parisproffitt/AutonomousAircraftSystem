"""Feature engineering for ML risk scoring and diagnostics."""

from __future__ import annotations

import numpy as np
import pandas as pd


ML_FEATURE_COLUMNS = [
    "airspeed_true_kt",
    "airspeed_meas_kt",
    "airspeed_error_kt",
    "vertical_speed_fpm",
    "pitch_deg",
    "roll_deg",
    "yaw_deg",
    "g_force_proxy",
    "angle_of_attack_proxy_deg",
    "control_effectiveness",
    "turbulence_index",
    "gps_confidence",
    "nav_position_error_m",
    "sensor_disagreement_score",
    "fuel_remaining_pct",
    "structural_margin_proxy",
    "approach_stability_index",
    "actuator_lag_ms",
    "comm_link_quality",
]


def build_ml_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build interpretable feature matrix for Isolation Forest."""
    feats = pd.DataFrame(index=df.index)

    for col in ML_FEATURE_COLUMNS:
        if col in df.columns:
            feats[col] = df[col]
        else:
            feats[col] = 0.0

    feats["ias_true_d1"] = df["airspeed_true_kt"].diff().fillna(0.0) if "airspeed_true_kt" in df.columns else 0.0
    feats["alt_d1"] = df["altitude_ft"].diff().fillna(0.0) if "altitude_ft" in df.columns else 0.0
    feats["roll_std_10"] = df["roll_deg"].rolling(10, min_periods=1).std().fillna(0.0) if "roll_deg" in df.columns else 0.0
    feats["ias_err_std_10"] = (
        df["airspeed_error_kt"].rolling(10, min_periods=1).std().fillna(0.0)
        if "airspeed_error_kt" in df.columns
        else 0.0
    )
    feats["vs_std_10"] = (
        df["vertical_speed_fpm"].rolling(10, min_periods=1).std().fillna(0.0)
        if "vertical_speed_fpm" in df.columns
        else 0.0
    )

    return feats.replace([np.inf, -np.inf], np.nan).fillna(0.0)


def build_trend_features(df: pd.DataFrame, window: int = 15) -> pd.DataFrame:
    """Rolling trend features for rule augmentation."""
    out = pd.DataFrame(index=df.index)
    if "airspeed_error_kt" in df.columns:
        out["ias_err_trend"] = df["airspeed_error_kt"].rolling(window, min_periods=3).mean()
    if "vertical_speed_fpm" in df.columns:
        out["vs_trend"] = df["vertical_speed_fpm"].rolling(window, min_periods=3).mean()
    if "gps_confidence" in df.columns:
        out["gps_trend"] = df["gps_confidence"].rolling(window, min_periods=3).mean()
    return out.fillna(0.0)
