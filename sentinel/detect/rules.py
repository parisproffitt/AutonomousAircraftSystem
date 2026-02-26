from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import pandas as pd


@dataclass(frozen=True)
class Incident:
    t: float
    severity: str  # "DEGRADED" or "CRITICAL"
    code: str
    message: str


def detect_incidents(df: pd.DataFrame) -> List[Incident]:
    """
    v0.1 rule-based detectors.
    Keeps it conservative + explainable.
    """
    incidents: List[Incident] = []

    for _, r in df.iterrows():
        t = float(r["t"])

        # 1) Excessive roll (proxy for stability issues)
        if float(r["roll_abs"]) > 20.0:
            incidents.append(
                Incident(
                    t=t,
                    severity="DEGRADED",
                    code="ROLL_EXCURSION",
                    message=f"Roll magnitude exceeded 20 deg (|roll|={float(r['roll_abs']):.1f}).",
                )
            )

        # 2) High descent rate near lower altitude (simple safety envelope)
        if float(r["altitude_ft"]) < 2500.0 and float(r["vs_fpm"]) < -1200.0:
            incidents.append(
                Incident(
                    t=t,
                    severity="CRITICAL",
                    code="LOW_ALT_HIGH_DESCENT",
                    message=f"High descent rate near low altitude (VS={float(r['vs_fpm']):.0f} fpm @ {float(r['altitude_ft']):.0f} ft).",
                )
            )

        # 3) Sensor disagreement proxy: persistent airspeed measurement error
        if abs(float(r["airspeed_err"])) > 8.0:
            incidents.append(
                Incident(
                    t=t,
                    severity="DEGRADED",
                    code="AIRSPEED_SENSOR_DISAGREE",
                    message=f"Airspeed measurement error exceeded 8 kt (err={float(r['airspeed_err']):.1f}).",
                )
            )

        # 4) Control degradation detection
        if float(r["control_effectiveness"]) < 0.65:
            incidents.append(
                Incident(
                    t=t,
                    severity="DEGRADED",
                    code="CONTROL_AUTHORITY_DEGRADED",
                    message=f"Control effectiveness reduced (eff={float(r['control_effectiveness']):.2f}).",
                )
            )

    # De-duplicate “spammy” repeats by keeping first occurrence per code
    first_by_code = {}
    for inc in incidents:
        if inc.code not in first_by_code:
            first_by_code[inc.code] = inc

    return list(first_by_code.values())