from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from autoflight.sim.mission import MissionConfig, run_mission
from autoflight.sim.failure_injection import FailureConfig
from autoflight.detect.rules import detect_incidents, Incident
from autoflight.detect.anomaly_ml import MLConfig, score_anomaly_risk
from autoflight.decide.policy_engine import decide, Decision


class FailureRequest(BaseModel):
    type: str = Field("none", pattern="^(none|pitot_drift|control_degradation|turbulence_burst)$")
    start_t: float = 90.0
    drift_rate: float = 0.03
    control_effectiveness: float = 0.6
    burst_intensity: float = 0.6
    burst_duration: float = 20.0

    def to_config(self) -> Optional[FailureConfig]:
        if self.type == "none":
            return None
        if self.type == "pitot_drift":
            return FailureConfig(
                name="pitot_drift",
                start_t=float(self.start_t),
                params={"drift_rate": float(self.drift_rate)},
            )
        if self.type == "control_degradation":
            return FailureConfig(
                name="control_degradation",
                start_t=float(self.start_t),
                params={"effectiveness": float(self.control_effectiveness)},
            )
        if self.type == "turbulence_burst":
            return FailureConfig(
                name="turbulence_burst",
                start_t=float(self.start_t),
                params={
                    "intensity": float(self.burst_intensity),
                    "duration": float(self.burst_duration),
                },
            )
        return None


class MissionRequest(BaseModel):
    duration_s: int = 300
    seed: int = 7
    noise_std: float = 0.05
    base_turbulence: float = 0.1

    enable_ml: bool = True
    ml_train_window_s: int = 60
    ml_contamination: float = 0.03
    ml_risk_threshold: float = 0.65


class MissionRun(BaseModel):
    mission: MissionRequest = MissionRequest()
    failure: FailureRequest = FailureRequest()


class TelemetryFrame(BaseModel):
    t: float
    altitude_ft: float
    airspeed_true: float
    airspeed_meas: float
    pitch_deg: float
    roll_deg: float
    control_effectiveness: float
    turbulence: float
    vs_fpm: float
    airspeed_err: float
    roll_abs: float
    incidents: List[Incident] = []
    ml_risk: Optional[float] = None
    decision: Optional[Decision] = None


def _run_pipeline(req: MissionRun):
    cfg = MissionConfig(
        duration_s=int(req.mission.duration_s),
        seed=int(req.mission.seed),
        noise_std=float(req.mission.noise_std),
        base_turbulence=float(req.mission.base_turbulence),
    )
    failure = req.failure.to_config()

    df = run_mission(cfg, failure=failure)
    incidents = detect_incidents(df)

    ml_peak = None
    ml_series = None
    if req.mission.enable_ml:
        ml_cfg = MLConfig(
            train_window_s=int(req.mission.ml_train_window_s),
            contamination=float(req.mission.ml_contamination),
            random_state=int(req.mission.seed),
            risk_threshold=float(req.mission.ml_risk_threshold),
        )
        ml_series, _ = score_anomaly_risk(df, ml_cfg)
        df["ml_risk"] = ml_series
        ml_peak = float(ml_series.max())

    decision = decide(
        incidents,
        ml_risk_peak=ml_peak,
        ml_risk_threshold=float(req.mission.ml_risk_threshold) if req.mission.enable_ml else None,
    )

    return df, incidents, ml_series, decision


def _build_frames(df, incidents: List[Incident], ml_series, decision: Decision) -> List[Dict[str, Any]]:
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

    # Attach final decision to the last frame for quick access
    if frames:
        frames[-1]["decision"] = {
            "safety_state": decision.safety_state,
            "action": decision.action,
            "explanation": decision.explanation,
        }
    return frames


app = FastAPI(title="Autonomous Flight Lab API", version="0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/mission/run")
def run_mission_once(req: MissionRun):
    df, incidents, ml_series, decision = _run_pipeline(req)
    frames = _build_frames(df, incidents, ml_series, decision)
    return {
        "decision": decision,
        "incidents": incidents,
        "frames": frames,
        "summary": {
            "ml_peak": float(ml_series.max()) if ml_series is not None else None,
            "duration_s": float(df["t"].iloc[-1]),
            "altitude_range_ft": [float(df["altitude_ft"].min()), float(df["altitude_ft"].max())],
            "airspeed_range_kt": [float(df["airspeed_true"].min()), float(df["airspeed_true"].max())],
        },
    }


@app.post("/api/mission/export")
def export_mission(req: MissionRun):
    df, incidents, ml_series, decision = _run_pipeline(req)
    frames = _build_frames(df, incidents, ml_series, decision)
    return {
        "frames": frames,
        "decision": decision,
        "incidents": incidents,
    }


@app.websocket("/ws/telemetry")
async def telemetry_stream(ws: WebSocket):
    await ws.accept()

    # Attempt to receive an optional config message
    try:
        msg = await asyncio.wait_for(ws.receive_json(), timeout=0.5)
        req = MissionRun(**msg)
    except Exception:
        req = MissionRun()  # defaults

    df, incidents, ml_series, decision = _run_pipeline(req)
    frames = _build_frames(df, incidents, ml_series, decision)

    try:
        for frame in frames:
            await ws.send_json(frame)
            await asyncio.sleep(0.02)  # 50 Hz stream for smooth Unity playback
        await ws.close()
    except WebSocketDisconnect:
        return
