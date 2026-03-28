# Unity 3D Overhaul Plan — Autonomous Flight Lab

## Vision
- Real‑time 3D mission viz in Unity: a modern fighter jet (F‑35 or similar) flying through dynamic atmospherics, with your anomaly detection and recovery logic driving cockpit alerts and autonomy behaviors.
- Keep the Python simulation/detection stack as the “mission brain”; Unity becomes the “glass cockpit + world”.

## Demo claims (target metrics)
- 99% simulated detection certainty on injected flight faults (pitot drift, control degradation, turbulence bursts).
- <1s autonomy decision latency from telemetry tick to policy output.
- <0.5% false-positive rate on nominal missions in simulation.

## Target Experience (demo script)
1) Pick a scenario: nominal, pitot drift, control degradation, turbulence burst.  
2) Launch: jet takes off, climbs to cruise; HUD shows speed/altitude/roll.  
3) Inject failure live: stream Python telemetry into Unity; cockpit warnings and aircraft response change visibly (e.g., oscillations with degraded controls, inaccurate airspeed due to pitot drift).  
4) Recovery: your policy engine recommends an action; Unity shows it (e.g., level off, throttle change, RTB cue) with on-screen annotations.  
5) Export clip: record a 20–60s replay video for sharing.

## Architecture (thin integration)
- **Python (existing):** keep `autoflight.sim.*`, `detect`, `decide`, `reporter`. Add a lightweight server to stream mission state.
- **Transport:** simple WebSocket or HTTP chunked JSON from Python to Unity.
- **Unity:** reads the stream, drives aircraft transforms, HUD, warnings, and camera moves.

### Proposed telemetry message (per tick)
```json
{
  "t": 42.0,
  "altitude_ft": 11850.3,
  "airspeed_true": 212.4,
  "airspeed_meas": 204.1,
  "pitch_deg": 2.3,
  "roll_deg": -4.8,
  "control_effectiveness": 0.63,
  "turbulence": 0.6,
  "vs_fpm": 120.0,
  "airspeed_err": -8.3,
  "incidents": [{"code": "PITOT_DRIFT", "severity": "medium"}],
  "decision": {"state": "degraded", "action": "level_off", "explanation": "..."}
}
```

## Unity build checklist
- Unity 2022/2023 LTS, URP template, Cinemachine, Input System.
- **Aircraft model:** licensed F‑35 (Asset Store/Sketchfab CC‑BY) or placeholder F‑16 until licensing is cleared.
- **Flight controller:** simple force-based flight model (lift/drag/thrust) mapped to telemetry; throttle/yoke driven by stream or player input.
- **HUD/MFD:** TextMeshPro overlays for speed/altitude/roll, incident callouts, policy recommendation banner.
- **Atmospherics:** volumetric clouds/fog, wind zones, turbulence gusts; lens dirt and camera shake for immersion.
- **Cameras:** Cinemachine FreeLook + “pilot cam” + “tail chase” + “orbital showcase”.
- **Failure visuals:** pitot drift → discrepant HUD airspeed; control degradation → sluggish roll/pitch; turbulence burst → sudden camera shake + roll excursions.
- **Recording:** enable Unity Recorder to export MP4 clips for demos.

## Python side (done here)
- `server.py` (FastAPI + WebSocket) streams mission ticks (`/ws/telemetry`) and exposes run/export endpoints (`/api/mission/run`, `/api/mission/export`).
- JSON export usable for offline Unity playback; frames include incidents and final decision.

## Unity implementation steps
1) Create URP project and import the jet model; set up materials and colliders.
2) Add scripts: `TelemetryClient` (WebSocket), `FlightVisualizer` (applies state to transforms), `HudController`, `IncidentBanner`, `CameraRigController`.
3) Build a simple skybox scene with runway, clouds, wind zone, and Cinemachine rigs.
4) Wire telemetry stream to aircraft pose + HUD + incident banners; add smoothing.
5) Map decision actions to animations (e.g., “RTB” triggers heading bug and turn‑to‑base).
6) Add input override so you can hand‑fly or let the Python policy fly.
7) Polish: particle trails on high roll rates, afterburner VFX when throttle > 90%, screen-space vignettes on high G or turbulence.
8) Record 2–3 showcase clips (nominal, pitot drift, control degradation).

## What you should do on your end
- Install Unity 2022/2023 LTS with URP; install Cinemachine, Recorder, Input System packages.
- Acquire/approve a legally usable F‑35 (or similar) model; confirm license for demo use.
- Stand up a new Unity project (`unity/AutonomousFlightShowcase`) and create the base scene with skybox, runway, and camera rigs.
- If you want live Python streaming: allow localhost WebSocket from Unity Editor; connect to `ws://localhost:8000/ws/telemetry` and optionally send mission/failure JSON on connect.
- If you prefer offline playback first: call `POST /api/mission/export` to generate a JSON file and play it back in Unity without networking; then add live streaming.
- Share which platform you want to target (Editor demo vs. Windows/macOS build) so we tune URP quality/performance accordingly.

## Fast follow items I can add here
- Unity-side C# stubs for `TelemetryClient` + `FlightVisualizer` (placed under `docs/` for copy/paste).
- Sample post-processing and HUD prefab definitions to match the telemetry fields.
