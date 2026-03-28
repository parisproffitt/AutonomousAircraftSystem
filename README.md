# Autonomous Flight & Fault Detection Simulation
Defense-inspired digital twin for jet flight fault detection with a Unity cockpit visualization.

## Overview
Simulates a modern fighter jet mission, injects failures, scores risk, and streams structured telemetry into a Unity 3D cockpit/airframe visualization. Built to showcase an explainable autonomy loop with measurable performance.

## Research Objective
Deliver rapid, interpretable detection of sensor faults and control degradation so autonomy policies can be stress-tested and visualized before flight testing.

## System Architecture
- Mission Telemetry Simulation  
- Failure Injection  
- Rule-Based Detection + Optional ML Risk  
- Decision & Explanation Engine  
- JSON Export & WebSocket Streaming  
- Unity Visualization Layer  
Layers are modular and connected by structured data contracts.

## Core Components
1) Mission Simulator — 300s climb/cruise; per-tick altitude, true/measured airspeed, pitch, roll, control effectiveness, turbulence, vs_fpm, airspeed error.  
2) Failure Injection — pitot drift (growing bias), control degradation (reduced authority), turbulence burst (short disturbance); configurable timing/magnitude.  
3) Detection & Risk — envelope rules (roll excursions, low-alt/high-descent, airspeed disagree, control authority loss) plus optional Isolation Forest escalation. Targets: **99% detection** on injected faults, **<0.5% FPR** nominal, **<1s latency** in simulation.  
4) Decision & Explanation — safety state + recommended action (continue/stabilize/reroute/abort) with plain-language rationale for HUD.  
5) Data Contracts & Streaming — HTTP (`/api/mission/run`, `/api/mission/export`) and WebSocket (`/ws/telemetry` ~50 Hz) with telemetry, incidents-to-date, ML risk (optional), final decision.

## Unity Visualization
- URP jet scene with HUD/MFD overlays and camera rigs.  
- Live telemetry drives pose, HUD metrics, incident banners, policy callouts.  
- Failure visuals: pitot drift → HUD airspeed disagreement; control degradation → sluggish response; turbulence burst → camera shake/roll excursions.  
- Capture 20–60s clips for nominal and faulted runs via Unity Recorder.

## Quantitative Scope
- 300s missions; 1s sim tick; ~50 Hz stream for visuals.  
- 3 injected failure modes; configurable timing/magnitude.  
- Risk scoring 0–1 with deterministic explanations.  
- JSON export for offline playback; WebSocket for real-time Unity.

## Real-World Applications 
- Autonomy/fault-detection demos and safety drills.  
- Digital-twin regression of policies before flight or hardware-in-loop.  
- Training aids that visualize sensor disagreement and degraded control authority.

## Run the Python API
- Install deps: `pip install -r requirements.txt`  
- Launch: `uvicorn server:app --reload --port 8000`  
- Health: `GET http://localhost:8000/api/health`  
- Run mission: `POST http://localhost:8000/api/mission/run`
  ```json
  {
    "mission": {"duration_s": 300, "seed": 7, "noise_std": 0.05, "base_turbulence": 0.1},
    "failure": {"type": "pitot_drift", "start_t": 90, "drift_rate": 0.03}
  }
  ```
- Export offline playback: `POST http://localhost:8000/api/mission/export` (frames + incidents + decision).  
- Live stream: WebSocket to `ws://localhost:8000/ws/telemetry`; optionally send the same JSON on connect; streams ~50 Hz.

## Unity workflow
- URP project `unity/AutonomousFlightShowcase` with Cinemachine + Recorder + Input System.  
- WebSocket/HTTP client ingests telemetry (t, altitude, airspeeds, pitch/roll, incidents, decision).  
- Capture clips for nominal and faulted scenarios.

## Roadmap
- [x] Python WebSocket/HTTP bridge for live streaming.  
- [x] Offline mission JSON exporter for Unity playback.  
- [ ] Unity C# stubs (TelemetryClient, FlightVisualizer, HUD controllers).  
- [ ] Finalize demo scenes and visual polish.
