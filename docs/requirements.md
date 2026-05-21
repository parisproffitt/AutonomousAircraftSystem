# Requirements

## Functional

| ID | Requirement | Status |
|----|-------------|--------|
| FR-01 | 50+ telemetry channels @ 1 Hz | Done |
| FR-02 | 30+ failure injection modes | Done |
| FR-03 | Rule detection: envelopes, trends, disagreement | Done |
| FR-04 | ML risk (Isolation Forest), advisory only | Done |
| FR-05 | Safety states NOMINAL → EMERGENCY | Done |
| FR-06 | Recovery actions through SAFE_TERMINATION | Done |
| FR-07 | Explanations for detections and decisions | Done |
| FR-08 | Streamlit mission console | Done |
| FR-09 | Six built-in presets | Done |
| FR-10 | JSON/Markdown reports | Done |
| FR-11 | pytest coverage | Done |

## Non-functional

| ID | Requirement |
|----|-------------|
| NFR-01 | Deterministic sim given seed |
| NFR-02 | Sub-second pipeline for 300 s missions (typical laptop) |
| NFR-03 | Runs offline |
| NFR-04 | Type hints on public APIs |

## Out of scope

Real avionics integration, actuator commands, DO-178C artifacts, classified platform modeling.
