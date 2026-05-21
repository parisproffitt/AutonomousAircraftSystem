"""Failure injection engine – 30+ simulated fault scenarios (non-operational)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np


@dataclass(frozen=True)
class FailureConfig:
    """Single failure event configuration."""

    name: str
    start_t: float
    params: Dict[str, Any] = field(default_factory=dict)
    end_t: Optional[float] = None


# Catalog of supported failure modes (30+)
FAILURE_CATALOG: Dict[str, str] = {
    "none": "No injected failure",
    "pitot_drift": "Pitot/static sensor drift – growing airspeed bias",
    "static_port_blockage": "Static port blockage – baro/altitude error",
    "gps_degradation": "GPS confidence degradation and position error growth",
    "gps_spoofing_proxy": "Navigation inconsistency proxy (spoofing-like)",
    "imu_bias_drift": "IMU bias drift – attitude rate errors",
    "magnetometer_interference": "Magnetometer interference – heading error",
    "actuator_lag": "Actuator response lag increase",
    "actuator_saturation": "Actuator saturation – limited deflection",
    "control_authority_loss": "Control effectiveness reduction",
    "elevator_stuck": "Elevator stuck at fixed deflection",
    "aileron_asymmetry": "Aileron asymmetric response",
    "rudder_limit": "Rudder authority limited",
    "turbulence_burst": "Severe turbulence burst",
    "wind_shear": "Wind shear event",
    "icing_proxy": "Icing accumulation proxy – degraded lift",
    "engine_thrust_degradation": "Engine thrust reduction",
    "engine_surge": "Engine surge – thrust oscillation",
    "fuel_leak": "Fuel leak – decreasing fuel remaining",
    "battery_degradation": "Battery SOC decline",
    "generator_failure": "Generator load spike / electrical stress",
    "comm_degradation": "Communication link degradation",
    "datalink_latency_spike": "Datalink latency spike",
    "sensor_disagreement": "Multi-sensor disagreement injection",
    "aoa_sensor_fault": "Angle-of-attack sensor fault",
    "radar_altimeter_fault": "Radar altimeter fault",
    "excessive_descent_rate": "Excessive descent rate command",
    "unstable_approach": "Unstable approach – path deviations",
    "autopilot_disconnect": "Autopilot disconnect event",
    "structural_load_spike": "Structural load margin reduction",
    "compound_pitot_gps": "Compound: pitot drift + GPS degradation",
    "compound_control_turb": "Compound: control loss + turbulence",
    "compound_approach": "Compound: unstable approach + sensor faults",
    "compound_engine_fuel": "Compound: thrust loss + fuel leak",
}


def list_failure_modes() -> List[str]:
    return [k for k in FAILURE_CATALOG if k != "none"]


def _elapsed(t: float, failure: FailureConfig) -> float:
    return max(0.0, t - failure.start_t)


def _active(t: float, failure: FailureConfig) -> bool:
    if t < failure.start_t:
        return False
    if failure.end_t is not None and t > failure.end_t:
        return False
    return True


def apply_failure(row: Dict[str, float], t: float, failure: FailureConfig) -> Dict[str, float]:
    """Apply a single failure to one telemetry row. Returns modified dict."""
    if not _active(t, failure):
        return row

    out = dict(row)
    dt = _elapsed(t, failure)
    p = failure.params
    name = failure.name

    if name == "pitot_drift":
        rate = float(p.get("drift_rate", 0.04))
        out["airspeed_meas_kt"] = out["airspeed_true_kt"] + rate * dt
        out["pitot_health"] = max(0.2, 1.0 - 0.02 * dt)

    elif name == "static_port_blockage":
        bias = float(p.get("alt_bias_ft", 80)) * min(1.0, dt / 30.0)
        out["baro_altitude_ft"] = out["altitude_ft"] + bias
        out["static_port_health"] = max(0.3, 1.0 - 0.03 * dt)

    elif name in ("gps_degradation", "gps_spoofing_proxy"):
        decay = float(p.get("confidence_decay", 0.02))
        out["gps_confidence"] = max(0.1, out["gps_confidence"] - decay * dt)
        out["nav_position_error_m"] = out["nav_position_error_m"] + float(p.get("error_growth", 2.0)) * dt

    elif name == "imu_bias_drift":
        out["pitch_deg"] = out["pitch_deg"] + float(p.get("pitch_bias", 0.05)) * dt
        out["roll_deg"] = out["roll_deg"] + float(p.get("roll_bias", 0.04)) * dt
        out["imu_health"] = max(0.25, 1.0 - 0.015 * dt)

    elif name == "magnetometer_interference":
        out["heading_deg"] = out["heading_deg"] + float(p.get("heading_error_deg", 1.5)) * np.sin(dt * 0.3)
        out["magnetometer_health"] = max(0.3, 0.9 - 0.02 * dt)

    elif name == "actuator_lag":
        lag = float(p.get("lag_ms", 120))
        out["actuator_lag_ms"] = max(out["actuator_lag_ms"], lag)
        out["actuator_response_ms"] = out["actuator_response_ms"] + lag * 0.5

    elif name == "actuator_saturation":
        out["elevator_deflection_proxy"] = float(p.get("elevator_limit", 0.35))
        out["actuator_response_ms"] *= 1.5

    elif name == "control_authority_loss":
        eff = float(p.get("effectiveness", 0.55))
        out["control_effectiveness"] = min(out["control_effectiveness"], eff)

    elif name == "elevator_stuck":
        out["elevator_deflection_proxy"] = float(p.get("stuck_deflection", 0.15))
        out["control_effectiveness"] = min(out["control_effectiveness"], 0.5)

    elif name == "aileron_asymmetry":
        out["aileron_deflection_proxy"] = float(p.get("asymmetry", 0.2))
        out["roll_deg"] = out["roll_deg"] + 3.0 * np.sin(dt * 0.5)

    elif name == "rudder_limit":
        out["rudder_deflection_proxy"] = float(p.get("limit", 0.25))
        out["yaw_rate_dps"] *= 0.6

    elif name == "turbulence_burst":
        duration = float(p.get("duration", 25.0))
        if dt <= duration:
            intensity = float(p.get("intensity", 0.75))
            out["turbulence_index"] = max(out["turbulence_index"], intensity)
            out["roll_deg"] += intensity * 8.0 * np.sin(dt * 1.2)
            out["g_force_proxy"] = max(out["g_force_proxy"], 1.0 + 0.4 * intensity)

    elif name == "wind_shear":
        if dt < float(p.get("duration", 15.0)):
            out["vertical_speed_fpm"] = out["vertical_speed_fpm"] - float(p.get("shear_fpm", 400))
            out["airspeed_true_kt"] -= float(p.get("ias_loss_kt", 8))

    elif name == "icing_proxy":
        out["angle_of_attack_proxy_deg"] += float(p.get("aoa_increase", 2.0)) * min(1.0, dt / 60.0)
        out["control_effectiveness"] *= max(0.5, 1.0 - 0.005 * dt)

    elif name == "engine_thrust_degradation":
        out["thrust_pct"] = max(float(p.get("min_thrust", 45)), out["thrust_pct"] - float(p.get("decay", 0.5)) * dt)
        out["engine_n1_pct"] = out["thrust_pct"] * 0.95

    elif name == "engine_surge":
        out["thrust_pct"] = out["thrust_pct"] * (1.0 + 0.15 * np.sin(dt * 2.0))
        out["engine_n1_pct"] = out["thrust_pct"]

    elif name == "fuel_leak":
        leak = float(p.get("leak_rate_pct_per_s", 0.08))
        out["fuel_remaining_pct"] = max(5.0, out["fuel_remaining_pct"] - leak * dt)
        out["fuel_flow_kgh"] = out["fuel_flow_kgh"] * 1.3

    elif name == "battery_degradation":
        out["battery_soc_pct"] = max(10.0, out["battery_soc_pct"] - float(p.get("drain", 0.1)) * dt)

    elif name == "generator_failure":
        out["generator_load_pct"] = min(100.0, out["generator_load_pct"] + float(p.get("spike", 3.0)) * dt)
        out["battery_voltage_v"] -= 0.02 * dt

    elif name == "comm_degradation":
        out["comm_link_quality"] = max(0.15, out["comm_link_quality"] - float(p.get("decay", 0.03)) * dt)

    elif name == "datalink_latency_spike":
        out["datalink_latency_ms"] = max(out["datalink_latency_ms"], float(p.get("latency_ms", 450)))

    elif name == "sensor_disagreement":
        out["airspeed_meas_kt"] = out["airspeed_true_kt"] + float(p.get("ias_bias", 6.0))
        out["baro_altitude_ft"] = out["altitude_ft"] - float(p.get("alt_bias", 50.0))
        out["sensor_disagreement_score"] = min(1.0, 0.3 + 0.02 * dt)

    elif name == "aoa_sensor_fault":
        out["aoa_sensor_health"] = max(0.2, 0.8 - 0.02 * dt)
        out["angle_of_attack_proxy_deg"] += float(p.get("aoa_error", 4.0))

    elif name == "radar_altimeter_fault":
        out["radar_altitude_ft"] = out["altitude_agl_ft"] + float(p.get("rag_error", 120))
        out["sensor_disagreement_score"] = max(out["sensor_disagreement_score"], 0.4)

    elif name == "excessive_descent_rate":
        out["vertical_speed_fpm"] = min(out["vertical_speed_fpm"], -float(p.get("vs_fpm", 1800)))

    elif name == "unstable_approach":
        out["approach_stability_index"] = max(0.1, 0.8 - 0.04 * dt)
        out["glideslope_deviation_dots"] = float(p.get("gs_dots", 1.8))
        out["localizer_deviation_dots"] = float(p.get("loc_dots", 0.9))
        out["descent_path_deviation_ft"] = float(p.get("path_dev_ft", 85))

    elif name == "autopilot_disconnect":
        out["autopilot_engaged"] = 0.0
        out["flight_director_active"] = 0.0

    elif name == "structural_load_spike":
        out["structural_margin_proxy"] = max(0.2, out["structural_margin_proxy"] - float(p.get("margin_loss", 0.03)) * dt)
        out["g_force_proxy"] = max(out["g_force_proxy"], float(p.get("g_peak", 2.2)))

    elif name == "compound_pitot_gps":
        out = apply_failure(out, t, FailureConfig("pitot_drift", failure.start_t, p))
        out = apply_failure(out, t, FailureConfig("gps_degradation", failure.start_t, p))

    elif name == "compound_control_turb":
        out = apply_failure(out, t, FailureConfig("control_authority_loss", failure.start_t, p))
        out = apply_failure(out, t, FailureConfig("turbulence_burst", failure.start_t, p))

    elif name == "compound_approach":
        out = apply_failure(out, t, FailureConfig("unstable_approach", failure.start_t, p))
        out = apply_failure(out, t, FailureConfig("sensor_disagreement", failure.start_t, p))

    elif name == "compound_engine_fuel":
        out = apply_failure(out, t, FailureConfig("engine_thrust_degradation", failure.start_t, p))
        out = apply_failure(out, t, FailureConfig("fuel_leak", failure.start_t, p))

    return out


def apply_failures(
    row: Dict[str, float],
    t: float,
    failures: List[FailureConfig],
) -> Dict[str, float]:
    """Apply multiple failures sequentially to a row."""
    out = row
    for f in failures:
        out = apply_failure(out, t, f)
    return out
