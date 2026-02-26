from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class FailureConfig:
    name: str
    start_t: float
    params: Dict[str, Any]


def apply_failures(row: Dict[str, float], t: float, failure: FailureConfig) -> Dict[str, float]:
    """
    Apply a single failure to a telemetry row. Returns a new dict.
    v0.1 supports:
      - pitot_drift: adds a growing bias to measured airspeed
      - control_degradation: reduces control_effectiveness after start
      - turbulence_burst: increases turbulence proxy for a window
    """
    out = dict(row)

    if t < failure.start_t:
        return out

    if failure.name == "pitot_drift":
        # bias grows linearly after start: bias = drift_rate * (t - start)
        drift_rate = float(failure.params.get("drift_rate", 0.03))  # knots/sec
        bias = drift_rate * (t - failure.start_t)
        out["airspeed_meas"] = out["airspeed_true"] + bias

    elif failure.name == "control_degradation":
        # step drop in effectiveness after start
        new_eff = float(failure.params.get("effectiveness", 0.6))
        out["control_effectiveness"] = min(out["control_effectiveness"], new_eff)

    elif failure.name == "turbulence_burst":
        # increase turbulence for a duration window
        intensity = float(failure.params.get("intensity", 0.5))
        duration = float(failure.params.get("duration", 20.0))
        if failure.start_t <= t <= (failure.start_t + duration):
            out["turbulence"] = max(out["turbulence"], intensity)

    return out