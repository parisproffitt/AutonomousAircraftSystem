# Autonomous Flight & Fault Detection Simulation
AI-driven flight failure detection and recovery system for autonomous aircraft. Streams explainable autonomy outputs into a Unity cockpit/airframe visualization.

---

## Overview
- Simulates modern fighter-jet telemetry (300s climb/cruise missions) with turbulence and control dynamics.  
- Injects representative faults: pitot drift, control degradation, turbulence bursts.  
- Detects and scores anomalies via rules + optional ML; targets **99% detection certainty**, **<0.5% false positives**, **<1s latency** in simulation.  
- Issues policy recommendations (continue / stabilize / reroute / abort) with plain-language rationales.  
- Streams structured JSON for live Unity viz and exports JSON for offline playback.

---

## Research Objective
Deliver rapid, interpretable detection and recovery for sensor faults and control degradation so autonomy policies can be stress-tested in a digital twin before flight.

---

## System Architecture
- Mission telemetry simulation  
- Failure injection  
- Rule-based detection + optional ML risk  
- Decision & explanation engine  
- JSON export & WebSocket streaming  
- Unity visualization layer  
Modules are loosely coupled via structured data contracts.

---

## Core Components
1) Mission simulator — per-tick altitude, true/measured airspeed, pitch, roll, control effectiveness, turbulence, vs_fpm, airspeed error (1 Hz base, ~50 Hz stream).  
2) Failure injection — pitot drift (growing bias), control degradation (reduced authority), turbulence burst (short disturbance); configurable timing/magnitude.  
3) Detection & risk — envelope rules (roll excursions, low-alt/high-descent, airspeed disagreement, control authority loss) + optional Isolation Forest escalation. Targets: **99% detection**, **<0.5% FPR**, **<1s decision latency** in sim.  
4) Decision & explanation — safety state + recommended action with concise rationale for HUD/cockpit cues.  
5) Data contracts & streaming — HTTP (`/api/mission/run`, `/api/mission/export`) and WebSocket (`/ws/telemetry` ~50 Hz) include telemetry, incidents-to-date, optional ML risk, and final decision.

---

## Unity Visualization 
- URP jet scene with HUD/MFD overlays and camera rigs.  
- Live telemetry drives pose, HUD metrics, incident banners, policy callouts.  
- Failure visuals: pitot drift → HUD airspeed disagreement; control degradation → sluggish response; turbulence burst → camera shake/roll excursions.  
- Record 20–60s clips (nominal and faulted) via Unity Recorder.

---

## Quantitative Scope
- 300s missions; 1s sim tick; ~50 Hz stream for visuals.  
- 3 fault modes; configurable timing/magnitude.  
- Risk scoring 0–1 with deterministic explanations.  
- JSON export for offline playback; WebSocket for real-time Unity.

---

## Real-World Applications
- Autonomy/fault-detection demos and safety drills.  
- Digital-twin regression of policies before flight or hardware-in-loop.  
- Training aids that visualize sensor disagreement and degraded control authority.

---

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
- CLI export: `python export_mission.py --out exports/mission_export.json --failure_type control_degradation`

---

## Unity Workflow 
- URP project `unity/AutonomousFlightShowcase` with Cinemachine + Recorder + Input System.  
- WebSocket/HTTP client ingests telemetry (t, altitude, airspeeds, pitch/roll, incidents, decision).  
- Capture clips for nominal and faulted scenarios.
- See `docs/telemetry_contract.md` for the per-frame JSON contract used by Unity.

---

## Roadmap
- [x] Python WebSocket/HTTP bridge for live streaming.  
- [x] Offline mission JSON exporter for Unity playback.  
- [ ] Unity C# stubs (TelemetryClient, FlightVisualizer, HUD controllers).  
- [ ] Finalize demo scenes and visual polish.
