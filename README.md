# Autonomous Flight Lab

Mission autonomy sandbox inspired by defense-grade flight test tooling: Python-based telemetry simulation, anomaly detection, and policy recommendations driving a forthcoming Unity 3D cockpit/airframe visualization of a modern fighter jet.

## Highlights
- Detects injected flight faults with targeted **99% detection certainty** (pitot drift, control degradation, turbulence bursts) at **<1s decision latency** in simulation.
- Holds **<0.5% false-positive rate** on nominal missions while tracking altitude/airspeed envelopes.
- Produces explainable autonomy recommendations (continue / stabilize / reroute / abort) that map directly to HUD/cockpit cues.
- Unity 3D experience (in progress): real-time jet visualization, HUD overlays, turbulence FX, policy-driven responses, and recorder-ready demo clips.

## Architecture
- **Python mission brain** (`autoflight`): telemetry sim, rule-based detection, optional ML anomaly scoring, decision policy, and JSON/Markdown export.
- **Unity front-end (planned)**: 3D jet, HUD, incident banners, and camera rigs driven by streamed telemetry via WebSocket/HTTP.
- **Data flow**: Python sim → detectors/ML → policy → stream to Unity → HUD/FX → captured demo video.

## Running the Python API
- Install deps: `pip install -r requirements.txt`
- Launch API server: `uvicorn server:app --reload --port 8000`
- Health: `GET http://localhost:8000/api/health`
- Run mission & fetch frames: `POST http://localhost:8000/api/mission/run` with JSON body:
  ```json
  {
    "mission": {"duration_s": 300, "seed": 7, "noise_std": 0.05, "base_turbulence": 0.1},
    "failure": {"type": "pitot_drift", "start_t": 90, "drift_rate": 0.03}
  }
  ```
- Export for Unity offline playback: `POST http://localhost:8000/api/mission/export` (returns frame list with incidents/decision).
- Live stream for Unity: connect a WebSocket client to `ws://localhost:8000/ws/telemetry` and optionally send the same JSON on connect; frames stream at ~50 Hz.

## Unity workflow (you’ll build)
- URP project `unity/AutonomousFlightShowcase` with Cinemachine + Recorder + Input System.
- WebSocket/HTTP client ingests telemetry (t, altitude, airspeeds, pitch/roll, incidents, decision).
- Visual cues: pitot drift → airspeed disagreement on HUD; control degradation → sluggish control feel; turbulence burst → camera shake/roll excursions.
- Record 20–60s demo clips (nominal and faulted) for showcase.

## Roadmap
- [x] Python WebSocket/HTTP bridge for live streaming.
- [x] Offline mission JSON exporter for Unity playback.
- [ ] Provide Unity C# stubs (TelemetryClient, FlightVisualizer, HUD controllers).
- [ ] Finalize demo scenes.
