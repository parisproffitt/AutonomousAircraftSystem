"""Tests for mission telemetry simulator."""

import pytest
import pandas as pd

from autoflight.sim.mission_simulator import MissionConfig, run_mission
from autoflight.sim.telemetry_schema import TELEMETRY_COLUMNS


def test_mission_produces_expected_duration():
    cfg = MissionConfig(duration_s=120, dt_s=1.0, seed=42)
    df = run_mission(cfg)
    assert len(df) == 121
    assert df["t"].iloc[-1] == 120.0


def test_telemetry_has_50_plus_columns():
    cfg = MissionConfig(duration_s=60, seed=1)
    df = run_mission(cfg)
    assert len(df.columns) >= 50


def test_key_channels_present():
    cfg = MissionConfig(duration_s=30, seed=2)
    df = run_mission(cfg)
    for col in ["altitude_ft", "airspeed_true_kt", "pitch_deg", "roll_deg", "gps_confidence"]:
        assert col in df.columns


def test_deterministic_with_seed():
    cfg = MissionConfig(duration_s=50, seed=99)
    df1 = run_mission(cfg)
    df2 = run_mission(cfg)
    pd.testing.assert_frame_equal(df1, df2)


def test_mission_phases_vary():
    cfg = MissionConfig(duration_s=300, seed=7)
    df = run_mission(cfg)
    assert df["mission_phase"].nunique() >= 3
