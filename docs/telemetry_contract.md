# Telemetry & Streaming Contract

## Message shape (per tick)
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
  "roll_abs": 4.8,
  "incidents": [{"t": 40, "severity": "DEGRADED", "code": "PITOT_DRIFT", "message": "..."}],
  "ml_risk": 0.42,
  "decision": {
    "safety_state": "DEGRADED",
    "action": "STABILIZE",
    "explanation": "pitot drift detected; stabilize and monitor"
  }
}
```

## Streaming endpoints
- HTTP run/export: `/api/mission/run`, `/api/mission/export`
- WebSocket live stream: `/ws/telemetry` (streams ~50 Hz for smooth Unity playback)

## Unity expectations
- Parse JSON into strongly-typed structs/classes.
- Drive aircraft transform from `pitch_deg`, `roll_deg`, and speed; use smoothing.
- HUD overlays: altitude, true/measured airspeed, pitch/roll, ml_risk (if present).
- Incident banners: show latest `incidents` entry; flash when severity changes.
- Decision callout: display `decision` (when present, at end-of-stream or latest).
- Visual cues: 
  - pitot drift → show airspeed disagreement on HUD
  - control degradation → dampen control authority/response
  - turbulence burst → camera shake + roll excursions

## Timing
- Simulation base tick: 1 Hz; stream at ~50 Hz for visuals.
- Final frame carries the decision summary for quick access.
