from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from autoflight.sim.mission import MissionConfig, run_mission
from autoflight.sim.failure_injection import FailureConfig
from autoflight.detect.rules import detect_incidents, Incident
from autoflight.detect.anomaly_ml import MLConfig, score_anomaly_risk
from autoflight.decide.policy_engine import decide, Decision


def build_failure(args) -> Optional[FailureConfig]:
    if args.failure_type == "none":
        return None
    if args.failure_type == "pitot_drift":
        return FailureConfig(
            name="pitot_drift",
            start_t=float(args.failure_start),
            params={"drift_rate": float(args.drift_rate)},
        )
    if args.failure_type == "control_degradation":
        return FailureConfig(
            name="control_degradation",
            start_t=float(args.failure_start),
            params={"effectiveness": float(args.control_effectiveness)},
        )
    if args.failure_type == "turbulence_burst":
        return FailureConfig(
            name="turbulence_burst",
            start_t=float(args.failure_start),
            params={
                "intensity": float(args.burst_intensity),
                "duration": float(args.burst_duration),
            },
        )
    return None


def build_frames(df, incidents: List[Incident], ml_series, decision: Decision) -> List[Dict[str, Any]]:
    frames: List[Dict[str, Any]] = []
    for idx, r in df.iterrows():
        t = float(r["t"])
        active_incs = [inc for inc in incidents if inc.t <= t]
        frame: Dict[str, Any] = {
            "t": t,
            "altitude_ft": float(r["altitude_ft"]),
            "airspeed_true": float(r["airspeed_true"]),
            "airspeed_meas": float(r["airspeed_meas"]),
            "pitch_deg": float(r["pitch_deg"]),
            "roll_deg": float(r["roll_deg"]),
            "control_effectiveness": float(r["control_effectiveness"]),
            "turbulence": float(r["turbulence"]),
            "vs_fpm": float(r["vs_fpm"]),
            "airspeed_err": float(r["airspeed_err"]),
            "roll_abs": float(r["roll_abs"]),
            "incidents": [inc.__dict__ for inc in active_incs],
        }
        if ml_series is not None:
            frame["ml_risk"] = float(ml_series.iloc[idx])
        frames.append(frame)

    if frames:
        frames[-1]["decision"] = {
            "safety_state": decision.safety_state,
            "action": decision.action,
            "explanation": decision.explanation,
        }
    return frames


def export(args):
    cfg = MissionConfig(
        duration_s=int(args.duration_s),
        seed=int(args.seed),
        noise_std=float(args.noise_std),
        base_turbulence=float(args.base_turbulence),
    )
    failure = build_failure(args)

    df = run_mission(cfg, failure=failure)
    incidents = detect_incidents(df)

    ml_series = None
    ml_peak = None
    if args.enable_ml:
        ml_cfg = MLConfig(
            train_window_s=int(args.ml_train_window_s),
            contamination=float(args.ml_contamination),
            random_state=int(args.seed),
            risk_threshold=float(args.ml_risk_threshold),
        )
        ml_series, _ = score_anomaly_risk(df, ml_cfg)
        df["ml_risk"] = ml_series
        ml_peak = float(ml_series.max())

    decision = decide(
        incidents,
        ml_risk_peak=ml_peak,
        ml_risk_threshold=float(args.ml_risk_threshold) if args.enable_ml else None,
    )

    frames = build_frames(df, incidents, ml_series, decision)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"frames": frames, "incidents": [i.__dict__ for i in incidents], "decision": {
        "safety_state": decision.safety_state,
        "action": decision.action,
        "explanation": decision.explanation,
    }}, indent=2), encoding="utf-8")
    print(f"Wrote {len(frames)} frames to {out_path}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Export a mission run to JSON for Unity playback.")
    p.add_argument("--duration_s", type=int, default=300)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--noise_std", type=float, default=0.05)
    p.add_argument("--base_turbulence", type=float, default=0.1)

    p.add_argument("--failure_type", type=str, default="none", choices=["none", "pitot_drift", "control_degradation", "turbulence_burst"])
    p.add_argument("--failure_start", type=float, default=90.0)
    p.add_argument("--drift_rate", type=float, default=0.03)
    p.add_argument("--control_effectiveness", type=float, default=0.6)
    p.add_argument("--burst_intensity", type=float, default=0.6)
    p.add_argument("--burst_duration", type=float, default=20.0)

    p.add_argument("--enable_ml", action="store_true", default=True)
    p.add_argument("--ml_train_window_s", type=int, default=60)
    p.add_argument("--ml_contamination", type=float, default=0.03)
    p.add_argument("--ml_risk_threshold", type=float, default=0.65)

    p.add_argument("--out", type=str, default="exports/mission_export.json")

    args = p.parse_args()
    export(args)
