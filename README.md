# Autonomous Flight Lab
AI-driven flight failure detection and recovery system for autonomous aircraft, paired with a Unity-based cockpit digital twin.

---

## System Snapshot
- Purpose: Detect and recover from flight faults in real time for autonomous jets.  
- Approach: Explainable autonomy loop (rules + optional ML) with a 3D digital twin.  
- Scale: 300s missions, 1 Hz simulation tick, ~50 Hz streaming for visuals.  
- Output: Risk score, safety state, and recommended action (continue / stabilize / reroute / abort) with plain-language rationale.  
- Stack: Python sim/detect/decision, JSON/WebSocket contracts, Unity (URP) cockpit viz.

---

## Overview
Simulates fighter-jet telemetry, injects representative failures, scores risk, and streams structured outputs into a Unity cockpit/airframe scene. Built to be modular, explainable, and measurable:
- **99% detection certainty** on injected faults (pitot drift, control degradation, turbulence bursts).  
- **<0.5% false positives** on nominal missions.  
- **<1s decision latency** from tick to policy output in simulation.  
- Plain-language recovery recommendations mapped to HUD/cockpit cues.  
- JSON streams for live Unity playback plus JSON export for offline review.

---

## Real-World Context
Autonomous aircraft need rapid, interpretable detection of sensor faults and control degradation. Traditional threshold alarms are brittle and lack scenario context. This digital twin stress-tests autonomy policies before flight.

---

## System Architecture
1. Mission Telemetry Simulation  
2. Failure Injection  
3. Rule-Based Detection + Optional ML Risk  
4. Decision & Explanation Engine  
5. JSON Export & WebSocket Streaming  
6. Unity Visualization Layer  
Modules are loosely coupled via structured data contracts.

---

## Core Components
1) Mission simulator — per-tick altitude, true/measured airspeed, pitch, roll, control effectiveness, turbulence, vs_fpm, airspeed error (1 Hz sim; ~50 Hz stream).  
2) Failure injection — pitot drift (growing bias), control degradation (reduced authority), turbulence burst (short disturbance); configurable timing/magnitude.  
3) Detection & risk — envelope rules (roll excursions, low-alt/high-descent, airspeed disagreement, control authority loss) plus optional Isolation Forest escalation. Targets: **99% detection**, **<0.5% FPR**, **<1s latency** in sim.  
4) Decision & explanation — safety state and recommended action with concise rationale for HUD/cockpit display.  
5) Data contracts & streaming — HTTP (`/api/mission/run`, `/api/mission/export`) and WebSocket (`/ws/telemetry` ~50 Hz) include telemetry, incidents-to-date, optional ML risk, and final decision. See `docs/telemetry_contract.md`.

---

## Unity Digital Twin Visualization (goal)
- URP jet scene with HUD/MFD overlays, incident banners, and camera rigs.  
- Live telemetry drives pose, HUD metrics, incident callouts, and policy cues.  
- Failure visuals: pitot drift → HUD airspeed disagreement; control degradation → sluggish response; turbulence burst → camera shake/roll excursions.  
- Media slots reserved for future screenshots/videos of nominal and faulted runs.

---

## Quantitative Scope
- 300s missions; 1s sim tick; ~50 Hz streaming for visuals.  
- 3 fault modes with configurable timing/magnitude.  
- Risk scoring 0–1 with deterministic explanations.  
- JSON export for offline playback; WebSocket for real-time Unity.

---

## Real-World Applications
- Autonomy/fault-detection demos and safety drills.  
- Digital-twin regression of policies before flight or hardware-in-loop.  
- Training aids that visualize sensor disagreement and degraded control authority.

---

## Unity Workflow (to build)
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
- [ ] Add media: demo screenshots and short clips (nominal + faulted).
