"""Root-cause diagnosis heuristics mapping incidents to likely failure modes."""

from __future__ import annotations

from typing import Dict, List

from autoflight.detect.rules import Incident


CODE_TO_LIKELY_FAILURE: Dict[str, List[str]] = {
    "AIRSPEED_SENSOR_DISAGREE": ["pitot_drift", "static_port_blockage", "sensor_disagreement"],
    "AIRSPEED_ERROR_TREND": ["pitot_drift", "pitot_drift"],
    "GPS_DEGRADED": ["gps_degradation", "gps_spoofing_proxy", "comm_degradation"],
    "CONTROL_AUTHORITY_DEGRADED": ["control_authority_loss", "actuator_lag", "icing_proxy"],
    "ACTUATOR_LAG": ["actuator_lag", "actuator_saturation"],
    "SEVERE_TURBULENCE": ["turbulence_burst", "wind_shear"],
    "UNSTABLE_APPROACH": ["unstable_approach", "compound_approach"],
    "LOW_FUEL": ["fuel_leak", "compound_engine_fuel"],
    "THRUST_DEGRADED": ["engine_thrust_degradation", "engine_surge"],
    "SENSOR_DISAGREEMENT": ["sensor_disagreement", "compound_pitot_gps"],
    "LOW_ALT_HIGH_DESCENT": ["excessive_descent_rate", "unstable_approach"],
    "COMM_DEGRADED": ["comm_degradation", "datalink_latency_spike"],
}


def diagnose(incidents: List[Incident]) -> List[Dict[str, str]]:
    """Return ranked likely failure hypotheses for detected incidents."""
    hypotheses: List[Dict[str, str]] = []
    for inc in incidents:
        candidates = CODE_TO_LIKELY_FAILURE.get(inc.code, ["unknown"])
        for rank, name in enumerate(candidates[:3], start=1):
            hypotheses.append(
                {
                    "incident_code": inc.code,
                    "likely_failure": name,
                    "confidence": "HIGH" if rank == 1 else ("MEDIUM" if rank == 2 else "LOW"),
                    "rationale": f"{inc.subsystem}: {inc.message}",
                }
            )
    return hypotheses
