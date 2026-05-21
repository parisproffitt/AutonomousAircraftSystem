"""Tests for failure injection engine."""

import pytest

from autoflight.sim.failure_injection import FailureConfig, apply_failure, list_failure_modes, FAILURE_CATALOG


def _base_row() -> dict:
    return {
        "t": 100.0,
        "airspeed_true_kt": 200.0,
        "airspeed_meas_kt": 200.0,
        "altitude_ft": 8000.0,
        "baro_altitude_ft": 8000.0,
        "control_effectiveness": 1.0,
        "turbulence_index": 0.1,
        "gps_confidence": 0.95,
        "nav_position_error_m": 2.0,
        "fuel_remaining_pct": 80.0,
        "vertical_speed_fpm": -500.0,
        "roll_deg": 2.0,
        "pitch_deg": 1.0,
        "g_force_proxy": 1.0,
        "actuator_lag_ms": 15.0,
        "comm_link_quality": 0.9,
        "approach_stability_index": 0.85,
        "sensor_disagreement_score": 0.05,
        "thrust_pct": 60.0,
        "engine_n1_pct": 58.0,
    }


def test_catalog_has_30_plus_modes():
    modes = list_failure_modes()
    assert len(modes) >= 30


def test_pitot_drift_increases_measured_ias():
    row = _base_row()
    f = FailureConfig("pitot_drift", start_t=90.0, params={"drift_rate": 0.1})
    out = apply_failure(row, t=110.0, failure=f)
    assert out["airspeed_meas_kt"] > out["airspeed_true_kt"]


def test_no_effect_before_start():
    row = _base_row()
    f = FailureConfig("control_authority_loss", start_t=200.0, params={"effectiveness": 0.4})
    out = apply_failure(row, t=100.0, failure=f)
    assert out["control_effectiveness"] == 1.0


def test_control_degradation_reduces_effectiveness():
    row = _base_row()
    f = FailureConfig("control_authority_loss", start_t=50.0, params={"effectiveness": 0.45})
    out = apply_failure(row, t=100.0, failure=f)
    assert out["control_effectiveness"] <= 0.45


def test_compound_failure_applies_multiple_effects():
    row = _base_row()
    f = FailureConfig("compound_pitot_gps", start_t=80.0, params={"drift_rate": 0.05})
    out = apply_failure(row, t=100.0, failure=f)
    assert out["airspeed_meas_kt"] != row["airspeed_meas_kt"] or out["gps_confidence"] < row["gps_confidence"]
