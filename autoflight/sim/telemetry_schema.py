"""Telemetry variable definitions for the flight simulator."""

from __future__ import annotations

from typing import List

# 50+ simulated aircraft telemetry channels
TELEMETRY_COLUMNS: List[str] = [
    "t",
    "mission_phase",
    # Position / kinematics
    "altitude_ft",
    "altitude_agl_ft",
    "airspeed_true_kt",
    "airspeed_meas_kt",
    "groundspeed_kt",
    "vertical_speed_fpm",
    "pitch_deg",
    "roll_deg",
    "yaw_deg",
    "heading_deg",
    "track_deg",
    "angle_of_attack_proxy_deg",
    "sideslip_proxy_deg",
    "g_force_proxy",
    "load_factor_proxy",
    # Rates
    "pitch_rate_dps",
    "roll_rate_dps",
    "yaw_rate_dps",
    # Propulsion / energy
    "thrust_pct",
    "engine_n1_pct",
    "fuel_remaining_pct",
    "fuel_flow_kgh",
    "battery_soc_pct",
    "battery_voltage_v",
    "generator_load_pct",
    # Control / actuation
    "control_effectiveness",
    "elevator_deflection_proxy",
    "aileron_deflection_proxy",
    "rudder_deflection_proxy",
    "actuator_response_ms",
    "actuator_lag_ms",
    "autopilot_engaged",
    "flight_director_active",
    # Environment
    "turbulence_index",
    "wind_speed_kt",
    "wind_direction_deg",
    "oat_c",
    "static_pressure_hpa",
    "dynamic_pressure_proxy",
    "density_altitude_ft",
    # Sensors / navigation
    "pitot_health",
    "static_port_health",
    "imu_health",
    "gps_confidence",
    "nav_position_error_m",
    "baro_altitude_ft",
    "radar_altitude_ft",
    "aoa_sensor_health",
    "magnetometer_health",
    "comm_link_quality",
    "datalink_latency_ms",
    # Structural / mission
    "structural_margin_proxy",
    "wing_loading_proxy",
    "approach_stability_index",
    "descent_path_deviation_ft",
    "glideslope_deviation_dots",
    "localizer_deviation_dots",
    # Derived (computed post-sim)
    "airspeed_error_kt",
    "altitude_error_ft",
    "sensor_disagreement_score",
    "energy_state_index",
]

MISSION_PHASES = ("PREFLIGHT", "TAKEOFF", "CLIMB", "CRUISE", "DESCENT", "APPROACH", "LANDING")
