# Autonomous Flight Lab
AI-driven flight failure detection and recovery system for autonomous aircraft, delivered through a Streamlit mission console.

---

## System Snapshot
- Purpose: Detect and recover from flight faults in real time for autonomous jets.  
- Approach: Explainable autonomy loop (rules + optional ML) with a Streamlit mission console.  
- Scale: 300s missions, 1 Hz simulation tick.  
- Output: Risk score, safety state, and recommended action (continue / stabilize / reroute / abort) with plain-language rationale.  
- Stack: Python sim/detect/decision, Streamlit front-end, JSON contracts.

---

## Overview
Simulates fighter-jet telemetry, injects representative failures, scores risk, and presents results in a Streamlit console. Built to be modular, explainable, and measurable:
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
5. Streamlit Mission Console (plots + incidents + summary)  
6. JSON Export (for replay/analysis)  
Modules are loosely coupled via structured data contracts.

---

## Core Components
1) Mission simulator — per-tick altitude, true/measured airspeed, pitch, roll, control effectiveness, turbulence, vs_fpm, airspeed error (1 Hz sim).  
2) Failure injection — pitot drift (growing bias), control degradation (reduced authority), turbulence burst (short disturbance); configurable timing/magnitude.  
3) Detection & risk — envelope rules (roll excursions, low-alt/high-descent, airspeed disagreement, control authority loss) plus optional Isolation Forest escalation. Targets: **99% detection**, **<0.5% FPR**, **<1s latency** in sim.  
4) Decision & explanation — safety state and recommended action with concise rationale for cockpit/mission display.  
5) Streamlit console — scenario controls, telemetry plots, incident table, ML risk chart, and decision summary.  
6) Data contracts — JSON export containing telemetry, incidents-to-date, optional ML risk, and final decision. See `docs/telemetry_contract.md`.

---

## Streamlit Experience
- Scenario controls for mission length, turbulence, noise, and fault injection.  
- Telemetry plots (altitude, true vs. measured airspeed, roll) and optional ML risk curve.  
- Incident table with severity, code, and message; decision summary with rationale.  
- Export JSON for offline review or integration elsewhere; media slots reserved for future screenshots/videos.

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

## Streamlit Workflow
- Run `streamlit run app.py` for scenario control, plots, incidents, and decision summaries.  
- See `docs/telemetry_contract.md` for the per-frame JSON contract used by other clients.

---
