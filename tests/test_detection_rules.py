"""Tests for rule-based anomaly detection."""

import pandas as pd

from autoflight.detect.rules import detect_incidents, ENVELOPE
from autoflight.sim.failure_injection import FailureConfig
from autoflight.sim.mission_simulator import MissionConfig, run_mission


def test_nominal_mission_low_incidents():
    df = run_mission(MissionConfig(duration_s=120, seed=7, noise_std=0.02))
    incidents = detect_incidents(df)
    assert len(incidents) <= 2


def test_pitot_drift_triggers_airspeed_disagree():
    df = run_mission(
        MissionConfig(duration_s=200, seed=11),
        failures=[FailureConfig("pitot_drift", start_t=60.0, params={"drift_rate": 0.12})],
    )
    incidents = detect_incidents(df)
    codes = {i.code for i in incidents}
    assert "AIRSPEED_SENSOR_DISAGREE" in codes or "AIRSPEED_ERROR_TREND" in codes


def test_control_degradation_detected():
    df = run_mission(
        MissionConfig(duration_s=200, seed=5),
        failures=[FailureConfig("control_authority_loss", start_t=50.0, params={"effectiveness": 0.45})],
    )
    incidents = detect_incidents(df)
    assert any(i.code == "CONTROL_AUTHORITY_DEGRADED" for i in incidents)


def test_incidents_have_explanations():
    df = run_mission(
        MissionConfig(duration_s=150, seed=3),
        failures=[FailureConfig("gps_degradation", start_t=40.0, params={"confidence_decay": 0.05})],
    )
    for inc in detect_incidents(df):
        assert inc.message
        assert inc.subsystem
