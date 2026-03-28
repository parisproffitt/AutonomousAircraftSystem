from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, Dict

import numpy as np
import pandas as pd

from autoflight.sim.failure_injection import FailureConfig, apply_failures


@dataclass(frozen=True)
class MissionConfig:
    duration_s: int = 300
    dt_s: float = 1.0
    seed: int = 7

    # nominal parameters
    climb_fpm: float = 800.0
    cruise_alt_ft: float = 12000.0
    cruise_airspeed_kt: float = 210.0

    # noise / disturbance
    noise_std: float = 0.05  # general noise scalar [0..1]
    base_turbulence: float = 0.1  # [0..1]


def run_mission(cfg: MissionConfig, failure: Optional[FailureConfig] = None) -> pd.DataFrame:
    """
    Generate a simulated mission telemetry DataFrame.
    This is intentionally simple (decision-layer prototype), but deterministic and trend-friendly.
    """
    rng = np.random.default_rng(cfg.seed)

    times = np.arange(0, cfg.duration_s + cfg.dt_s, cfg.dt_s)

    altitude_ft = np.zeros_like(times, dtype=float)
    airspeed_true = np.zeros_like(times, dtype=float)
    pitch_deg = np.zeros_like(times, dtype=float)
    roll_deg = np.zeros_like(times, dtype=float)

    # Start conditions
    altitude_ft[0] = 1500.0
    airspeed_true[0] = 160.0

    control_effectiveness = 1.0
    turbulence = cfg.base_turbulence

    # Simple “mission phases”
    # - climb until cruise altitude
    # - then hold altitude and speed near cruise
    for i in range(1, len(times)):
        t = times[i]

        # nominal turbulence noise grows with turbulence scalar
        turb_noise = turbulence * rng.normal(0.0, 1.0)

        # Altitude dynamics
        if altitude_ft[i - 1] < cfg.cruise_alt_ft:
            climb_rate_fps = (cfg.climb_fpm / 60.0)
            altitude_ft[i] = altitude_ft[i - 1] + climb_rate_fps * cfg.dt_s
            pitch_deg[i] = 6.0 + 1.5 * turb_noise
        else:
            altitude_ft[i] = altitude_ft[i - 1] + 0.2 * turb_noise  # small hold jitter
            pitch_deg[i] = 2.0 + 1.0 * turb_noise

        # Airspeed dynamics (simple approach to cruise speed)
        target = cfg.cruise_airspeed_kt
        # control effectiveness influences how well we track target
        airspeed_true[i] = airspeed_true[i - 1] + control_effectiveness * 0.15 * (target - airspeed_true[i - 1])
        airspeed_true[i] += cfg.noise_std * 2.0 * rng.normal(0.0, 1.0) + 0.3 * turb_noise

        # Roll responds to turbulence; more turbulence => more roll excursions
        roll_deg[i] = 2.0 * turb_noise

        # Build row for failure application
        row = {
            "t": float(t),
            "altitude_ft": float(altitude_ft[i]),
            "airspeed_true": float(airspeed_true[i]),
            "airspeed_meas": float(airspeed_true[i]),  # measured starts nominal
            "pitch_deg": float(pitch_deg[i]),
            "roll_deg": float(roll_deg[i]),
            "control_effectiveness": float(control_effectiveness),
            "turbulence": float(turbulence),
        }

        # Apply failure (may modify airspeed_meas/control_effectiveness/turbulence)
        if failure is not None:
            row = apply_failures(row, t=float(t), failure=failure)

        # Persist any “stateful” failure effects (effectiveness/turbulence)
        control_effectiveness = float(row["control_effectiveness"])
        turbulence = float(row["turbulence"])

        # Overwrite arrays with any failure changes
        altitude_ft[i] = row["altitude_ft"]
        airspeed_true[i] = row["airspeed_true"]

        # Store measured separately in dataframe later (we keep in row only)

        # Save current row into a list
        if i == 1:
            rows: List[Dict[str, float]] = []
            # also include t=0 initial row
            rows.append(
                {
                    "t": float(times[0]),
                    "altitude_ft": float(altitude_ft[0]),
                    "airspeed_true": float(airspeed_true[0]),
                    "airspeed_meas": float(airspeed_true[0]),
                    "pitch_deg": 4.0,
                    "roll_deg": 0.0,
                    "control_effectiveness": 1.0,
                    "turbulence": cfg.base_turbulence,
                }
            )

        rows.append(row)

    df = pd.DataFrame(rows)

    # Derived signals (useful for detectors)
    df["vs_fpm"] = df["altitude_ft"].diff().fillna(0.0) * (60.0 / cfg.dt_s)
    df["airspeed_err"] = df["airspeed_meas"] - df["airspeed_true"]
    df["roll_abs"] = df["roll_deg"].abs()

    return df