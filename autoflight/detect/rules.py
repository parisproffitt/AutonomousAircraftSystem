"""Deterministic rule-based anomaly detection – envelopes, trends, disagreement."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pandas as pd

from autoflight.features.engineering import build_trend_features


@dataclass(frozen=True)
class Incident:
    t: float
    severity: str  # DEGRADED | CRITICAL | EMERGENCY
    code: str
    message: str
    subsystem: str = "GENERAL"


# Envelope thresholds (tunable, documented in verification.md)
ENVELOPE = {
    "roll_max_deg": 25.0,
    "pitch_max_deg": 30.0,
    "g_max": 2.5,
    "ias_err_max_kt": 10.0,
    "vs_descent_critical_fpm": -1500.0,
    "low_alt_ft": 2000.0,
    "control_eff_min": 0.60,
    "gps_conf_min": 0.50,
    "sensor_disagree_max": 0.55,
    "fuel_min_pct": 15.0,
    "structural_margin_min": 0.35,
    "approach_stability_min": 0.40,
    "comm_quality_min": 0.35,
    "actuator_lag_max_ms": 200.0,
}


def detect_incidents(df: pd.DataFrame) -> List[Incident]:
    """
    Rule-based detection: envelope checks, trend analysis, sensor disagreement,
    and unsafe-condition detection. Returns de-duplicated first-occurrence per code.
    """
    incidents: List[Incident] = []
    trends = build_trend_features(df)

    for idx, r in df.iterrows():
        t = float(r["t"])
        phase_idx = int(r.get("mission_phase", 2))
        is_low_alt = float(r["altitude_ft"]) < ENVELOPE["low_alt_ft"]
        is_approach = phase_idx >= 4  # DESCENT/APPROACH/LANDING

        # Envelope: roll
        roll_abs = abs(float(r.get("roll_deg", 0)))
        if roll_abs > ENVELOPE["roll_max_deg"]:
            incidents.append(
                Incident(
                    t=t,
                    severity="DEGRADED",
                    code="ROLL_EXCURSION",
                    message=f"Roll exceeded envelope ({roll_abs:.1f}° > {ENVELOPE['roll_max_deg']:.0f}°).",
                    subsystem="FLIGHT_CONTROLS",
                )
            )

        # Envelope: pitch
        if abs(float(r.get("pitch_deg", 0))) > ENVELOPE["pitch_max_deg"]:
            incidents.append(
                Incident(
                    t=t,
                    severity="DEGRADED",
                    code="PITCH_EXCURSION",
                    message=f"Pitch exceeded safe envelope ({float(r['pitch_deg']):.1f}°).",
                    subsystem="FLIGHT_CONTROLS",
                )
            )

        # G-force
        if float(r.get("g_force_proxy", 1.0)) > ENVELOPE["g_max"]:
            incidents.append(
                Incident(
                    t=t,
                    severity="CRITICAL",
                    code="HIGH_G_LOAD",
                    message=f"G-load proxy exceeded limit ({float(r['g_force_proxy']):.2f}g).",
                    subsystem="STRUCTURAL",
                )
            )

        # Sensor disagreement – airspeed
        ias_err = abs(float(r.get("airspeed_error_kt", 0)))
        if ias_err > ENVELOPE["ias_err_max_kt"]:
            incidents.append(
                Incident(
                    t=t,
                    severity="DEGRADED",
                    code="AIRSPEED_SENSOR_DISAGREE",
                    message=f"Airspeed measurement error {ias_err:.1f} kt exceeds {ENVELOPE['ias_err_max_kt']:.0f} kt.",
                    subsystem="AIR_DATA",
                )
            )

        # Trend: growing airspeed error
        if idx in trends.index and abs(float(trends.loc[idx, "ias_err_trend"])) > 6.0:
            incidents.append(
                Incident(
                    t=t,
                    severity="DEGRADED",
                    code="AIRSPEED_ERROR_TREND",
                    message="Sustained trend in airspeed measurement error indicates pitot/static drift.",
                    subsystem="AIR_DATA",
                )
            )

        # Low altitude + high descent
        vs = float(r.get("vertical_speed_fpm", 0))
        if is_low_alt and vs < ENVELOPE["vs_descent_critical_fpm"]:
            incidents.append(
                Incident(
                    t=t,
                    severity="CRITICAL",
                    code="LOW_ALT_HIGH_DESCENT",
                    message=f"Excessive descent {vs:.0f} fpm below {ENVELOPE['low_alt_ft']:.0f} ft.",
                    subsystem="TRAJECTORY",
                )
            )

        # Control authority
        if float(r.get("control_effectiveness", 1.0)) < ENVELOPE["control_eff_min"]:
            incidents.append(
                Incident(
                    t=t,
                    severity="DEGRADED",
                    code="CONTROL_AUTHORITY_DEGRADED",
                    message=f"Control effectiveness {float(r['control_effectiveness']):.2f} below minimum.",
                    subsystem="FLIGHT_CONTROLS",
                )
            )

        # GPS
        if float(r.get("gps_confidence", 1.0)) < ENVELOPE["gps_conf_min"]:
            incidents.append(
                Incident(
                    t=t,
                    severity="DEGRADED",
                    code="GPS_DEGRADED",
                    message=f"GPS confidence {float(r['gps_confidence']):.2f} below threshold.",
                    subsystem="NAVIGATION",
                )
            )

        # Composite sensor disagreement score
        sd = float(r.get("sensor_disagreement_score", 0))
        if sd > ENVELOPE["sensor_disagree_max"]:
            incidents.append(
                Incident(
                    t=t,
                    severity="DEGRADED",
                    code="SENSOR_DISAGREEMENT",
                    message=f"Multi-sensor disagreement score {sd:.2f} elevated.",
                    subsystem="SENSORS",
                )
            )

        # Fuel
        if float(r.get("fuel_remaining_pct", 100)) < ENVELOPE["fuel_min_pct"]:
            incidents.append(
                Incident(
                    t=t,
                    severity="CRITICAL",
                    code="LOW_FUEL",
                    message=f"Fuel remaining {float(r['fuel_remaining_pct']):.1f}% critical.",
                    subsystem="PROPULSION",
                )
            )

        # Structural margin
        if float(r.get("structural_margin_proxy", 1.0)) < ENVELOPE["structural_margin_min"]:
            incidents.append(
                Incident(
                    t=t,
                    severity="CRITICAL",
                    code="STRUCTURAL_MARGIN_LOW",
                    message="Structural margin proxy below safe threshold.",
                    subsystem="STRUCTURAL",
                )
            )

        # Unstable approach
        if is_approach and float(r.get("approach_stability_index", 1.0)) < ENVELOPE["approach_stability_min"]:
            incidents.append(
                Incident(
                    t=t,
                    severity="CRITICAL",
                    code="UNSTABLE_APPROACH",
                    message=f"Unstable approach (stability index {float(r['approach_stability_index']):.2f}).",
                    subsystem="TRAJECTORY",
                )
            )

        # Communications
        if float(r.get("comm_link_quality", 1.0)) < ENVELOPE["comm_quality_min"]:
            incidents.append(
                Incident(
                    t=t,
                    severity="DEGRADED",
                    code="COMM_DEGRADED",
                    message="Communication link quality degraded.",
                    subsystem="COMMS",
                )
            )

        # Actuator lag
        if float(r.get("actuator_lag_ms", 0)) > ENVELOPE["actuator_lag_max_ms"]:
            incidents.append(
                Incident(
                    t=t,
                    severity="DEGRADED",
                    code="ACTUATOR_LAG",
                    message=f"Actuator lag {float(r['actuator_lag_ms']):.0f} ms exceeds limit.",
                    subsystem="FLIGHT_CONTROLS",
                )
            )

        # Engine thrust
        if float(r.get("thrust_pct", 100)) < 40.0 and phase_idx < 4:
            incidents.append(
                Incident(
                    t=t,
                    severity="CRITICAL",
                    code="THRUST_DEGRADED",
                    message=f"Engine thrust {float(r['thrust_pct']):.0f}% insufficient for phase.",
                    subsystem="PROPULSION",
                )
            )

        # Turbulence burst proxy
        if float(r.get("turbulence_index", 0)) > 0.65:
            incidents.append(
                Incident(
                    t=t,
                    severity="DEGRADED",
                    code="SEVERE_TURBULENCE",
                    message=f"Severe turbulence index {float(r['turbulence_index']):.2f}.",
                    subsystem="ENVIRONMENT",
                )
            )

    # De-duplicate: first occurrence per code
    seen: dict[str, Incident] = {}
    for inc in sorted(incidents, key=lambda x: x.t):
        if inc.code not in seen:
            seen[inc.code] = inc
    return list(seen.values())
