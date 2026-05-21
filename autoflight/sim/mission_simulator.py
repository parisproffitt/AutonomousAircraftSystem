"""Deterministic mission telemetry simulator – 50+ channels, phased flight profile."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from autoflight.sim.failure_injection import FailureConfig, apply_failures
from autoflight.sim.telemetry_schema import MISSION_PHASES, TELEMETRY_COLUMNS


@dataclass(frozen=True)
class MissionConfig:
    duration_s: int = 300
    dt_s: float = 1.0
    seed: int = 7
    cruise_alt_ft: float = 12000.0
    cruise_ias_kt: float = 220.0
    climb_fpm: float = 900.0
    noise_std: float = 0.04
    base_turbulence: float = 0.08


def _phase_for_t(t: float, duration: float) -> str:
    """Map mission time to flight phase."""
    ratio = t / max(duration, 1.0)
    if ratio < 0.05:
        return "TAKEOFF"
    if ratio < 0.25:
        return "CLIMB"
    if ratio < 0.55:
        return "CRUISE"
    if ratio < 0.75:
        return "DESCENT"
    if ratio < 0.92:
        return "APPROACH"
    if ratio < 0.98:
        return "LANDING"
    return "PREFLIGHT" if t < 1 else "CRUISE"


def _base_row(
    t: float,
    cfg: MissionConfig,
    rng: np.random.Generator,
    state: Dict[str, float],
) -> Dict[str, float]:
    """Generate nominal telemetry for time t given propagated state."""
    duration = float(cfg.duration_s)
    phase = _phase_for_t(t, duration)
    noise = cfg.noise_std

    alt = state["altitude_ft"]
    ias = state["airspeed_true_kt"]
    turb = state["turbulence_index"]
    ce = state["control_effectiveness"]
    fuel = state["fuel_remaining_pct"]

    turb_n = turb * rng.normal(0, 1)
    vs_fpm = state.get("vertical_speed_fpm", 0.0)

    pitch = 3.0 if phase in ("CLIMB", "TAKEOFF") else (1.5 if phase == "CRUISE" else -2.5)
    pitch += 1.2 * turb_n + noise * rng.normal(0, 1)

    roll = 2.5 * turb_n + noise * 0.8 * rng.normal(0, 1)
    yaw = 0.5 * turb_n

    row: Dict[str, float] = {
        "t": t,
        "mission_phase": float(MISSION_PHASES.index(phase) if phase in MISSION_PHASES else 2),
        "altitude_ft": alt,
        "altitude_agl_ft": max(0, alt - 1200) if phase in ("APPROACH", "LANDING") else alt * 0.1,
        "airspeed_true_kt": ias,
        "airspeed_meas_kt": ias,
        "groundspeed_kt": ias * 0.98,
        "vertical_speed_fpm": vs_fpm,
        "pitch_deg": pitch,
        "roll_deg": roll,
        "yaw_deg": yaw,
        "heading_deg": 270.0 + 0.1 * t,
        "track_deg": 269.5 + 0.08 * t,
        "angle_of_attack_proxy_deg": 4.0 + 0.01 * ias,
        "sideslip_proxy_deg": 0.3 * turb_n,
        "g_force_proxy": 1.0 + 0.15 * abs(turb_n),
        "load_factor_proxy": 1.0 + 0.1 * abs(turb_n),
        "pitch_rate_dps": 0.5 * turb_n,
        "roll_rate_dps": 1.2 * turb_n,
        "yaw_rate_dps": 0.3 * turb_n,
        "thrust_pct": 72.0 if phase != "CRUISE" else 58.0,
        "engine_n1_pct": 75.0,
        "fuel_remaining_pct": fuel,
        "fuel_flow_kgh": 420.0 + 10 * turb,
        "battery_soc_pct": 88.0,
        "battery_voltage_v": 28.2,
        "generator_load_pct": 45.0,
        "control_effectiveness": ce,
        "elevator_deflection_proxy": 0.08,
        "aileron_deflection_proxy": 0.02 * roll,
        "rudder_deflection_proxy": 0.01 * yaw,
        "actuator_response_ms": 35.0,
        "actuator_lag_ms": 12.0,
        "autopilot_engaged": 1.0 if phase not in ("TAKEOFF", "LANDING") else 0.0,
        "flight_director_active": 1.0,
        "turbulence_index": turb,
        "wind_speed_kt": 12.0 + 3 * turb,
        "wind_direction_deg": 240.0,
        "oat_c": 15.0 - alt / 1000.0 * 2.0,
        "static_pressure_hpa": 1013.0 - alt / 30.0,
        "dynamic_pressure_proxy": 0.003 * ias**2,
        "density_altitude_ft": alt + 200,
        "pitot_health": 1.0,
        "static_port_health": 1.0,
        "imu_health": 1.0,
        "gps_confidence": 0.95,
        "nav_position_error_m": 2.5,
        "baro_altitude_ft": alt,
        "radar_altitude_ft": max(0, alt - 1200),
        "aoa_sensor_health": 1.0,
        "magnetometer_health": 1.0,
        "comm_link_quality": 0.92,
        "datalink_latency_ms": 45.0,
        "structural_margin_proxy": 0.85,
        "wing_loading_proxy": 0.55,
        "approach_stability_index": 0.9 if phase != "APPROACH" else 0.75,
        "descent_path_deviation_ft": 15.0 if phase == "APPROACH" else 5.0,
        "glideslope_deviation_dots": 0.3,
        "localizer_deviation_dots": 0.2,
        "airspeed_error_kt": 0.0,
        "altitude_error_ft": 0.0,
        "sensor_disagreement_score": 0.05,
        "energy_state_index": fuel / 100.0 * (ias / 250.0),
    }
    return row


def run_mission(
    cfg: MissionConfig,
    failures: Optional[List[FailureConfig]] = None,
) -> pd.DataFrame:
    """
    Simulate a full mission and return telemetry DataFrame with 50+ columns.
    Deterministic given seed; suitable for rule/ML pipelines.
    """
    rng = np.random.default_rng(cfg.seed)
    failures = failures or []
    times = np.arange(0, cfg.duration_s + cfg.dt_s, cfg.dt_s)

    state: Dict[str, float] = {
        "altitude_ft": 800.0,
        "airspeed_true_kt": 155.0,
        "turbulence_index": cfg.base_turbulence,
        "control_effectiveness": 1.0,
        "fuel_remaining_pct": 92.0,
        "vertical_speed_fpm": cfg.climb_fpm,
    }

    rows: List[Dict[str, float]] = []

    for t in times:
        phase = _phase_for_t(float(t), float(cfg.duration_s))

        # Propagate kinematics
        if phase in ("TAKEOFF", "CLIMB") and state["altitude_ft"] < cfg.cruise_alt_ft:
            state["vertical_speed_fpm"] = cfg.climb_fpm + rng.normal(0, 30)
            state["altitude_ft"] += (state["vertical_speed_fpm"] / 60.0) * cfg.dt_s
        elif phase == "CRUISE":
            state["vertical_speed_fpm"] = 50 * rng.normal(0, 1)
            state["altitude_ft"] += (state["vertical_speed_fpm"] / 60.0) * cfg.dt_s
            state["altitude_ft"] = min(state["altitude_ft"], cfg.cruise_alt_ft + 100)
        elif phase in ("DESCENT", "APPROACH", "LANDING"):
            vs = -900.0 if phase == "DESCENT" else (-1100.0 if phase == "APPROACH" else -600.0)
            state["vertical_speed_fpm"] = vs + rng.normal(0, 40)
            state["altitude_ft"] = max(0, state["altitude_ft"] + (state["vertical_speed_fpm"] / 60.0) * cfg.dt_s)

        target_ias = cfg.cruise_ias_kt
        if phase == "APPROACH":
            target_ias = 145.0
        elif phase == "TAKEOFF":
            target_ias = 165.0

        ce = state["control_effectiveness"]
        state["airspeed_true_kt"] += ce * 0.12 * (target_ias - state["airspeed_true_kt"])
        state["airspeed_true_kt"] += cfg.noise_std * 3 * rng.normal(0, 1)

        row = _base_row(float(t), cfg, rng, state)
        row = apply_failures(row, float(t), failures)

        state["control_effectiveness"] = float(row["control_effectiveness"])
        state["turbulence_index"] = float(row["turbulence_index"])
        state["fuel_remaining_pct"] = float(row["fuel_remaining_pct"])

        rows.append(row)

    df = pd.DataFrame(rows)

    # Derived signals
    df["airspeed_error_kt"] = df["airspeed_meas_kt"] - df["airspeed_true_kt"]
    df["altitude_error_ft"] = df["baro_altitude_ft"] - df["altitude_ft"]
    df["sensor_disagreement_score"] = (
        (df["airspeed_error_kt"].abs() / 15.0).clip(0, 1) * 0.4
        + (df["altitude_error_ft"].abs() / 200.0).clip(0, 1) * 0.3
        + (1.0 - df["gps_confidence"]).clip(0, 1) * 0.3
    ).clip(0, 1)

    # Ensure all schema columns exist
    for col in TELEMETRY_COLUMNS:
        if col not in df.columns and col != "mission_phase":
            df[col] = 0.0

    df["roll_abs_deg"] = df["roll_deg"].abs()
    df["pitch_abs_deg"] = df["pitch_deg"].abs()

    return df
