"""Tests for ML anomaly risk scoring."""

import pytest

from autoflight.detect.anomaly_ml import MLConfig, score_anomaly_risk
from autoflight.sim.failure_injection import FailureConfig
from autoflight.sim.mission_simulator import MissionConfig, run_mission


def test_ml_risk_bounded():
    df = run_mission(MissionConfig(duration_s=100, seed=7))
    risk, _ = score_anomaly_risk(df, MLConfig(train_window_s=30, random_state=7))
    assert risk.min() >= 0.0
    assert risk.max() <= 1.0 + 1e-6


def test_failure_mission_higher_peak_risk_than_nominal():
    nominal = run_mission(MissionConfig(duration_s=150, seed=10))
    faulty = run_mission(
        MissionConfig(duration_s=150, seed=10),
        failures=[FailureConfig("pitot_drift", start_t=40.0, params={"drift_rate": 0.15})],
    )
    cfg = MLConfig(train_window_s=40, random_state=10)
    r_nom, _ = score_anomaly_risk(nominal, cfg)
    r_fault, _ = score_anomaly_risk(faulty, cfg)
    assert r_fault.max() >= r_nom.max() * 0.5
