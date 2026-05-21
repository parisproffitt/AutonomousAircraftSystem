# Scenario catalog

## Built-in presets

| ID | Name | Failure(s) | Notes |
|----|------|------------|-------|
| `nominal_mission` | Nominal Mission | None | Baseline |
| `pitot_drift` | Pitot / Static Drift | `pitot_drift` @ 90s | Airspeed disagree |
| `turbulence_approach` | Turbulence During Approach | `turbulence_burst` @ 230s | Approach phase |
| `control_degradation` | Control Authority Degradation | control + actuator lag | Degraded controls |
| `gps_degradation` | GPS Degradation | `gps_degradation` @ 100s | Navigation |
| `compound_failure` | Compound Failure | `compound_pitot_gps` @ 85s | Multi-sensor |

## Failure modes (33)

| Mode | Category |
|------|----------|
| `pitot_drift` | Air data |
| `static_port_blockage` | Air data |
| `gps_degradation` | Navigation |
| `gps_spoofing_proxy` | Navigation |
| `imu_bias_drift` | Sensors |
| `magnetometer_interference` | Sensors |
| `actuator_lag` | Controls |
| `actuator_saturation` | Controls |
| `control_authority_loss` | Controls |
| `elevator_stuck` | Controls |
| `aileron_asymmetry` | Controls |
| `rudder_limit` | Controls |
| `turbulence_burst` | Environment |
| `wind_shear` | Environment |
| `icing_proxy` | Environment |
| `engine_thrust_degradation` | Propulsion |
| `engine_surge` | Propulsion |
| `fuel_leak` | Propulsion |
| `battery_degradation` | Electrical |
| `generator_failure` | Electrical |
| `comm_degradation` | Comms |
| `datalink_latency_spike` | Comms |
| `sensor_disagreement` | Sensors |
| `aoa_sensor_fault` | Sensors |
| `radar_altimeter_fault` | Sensors |
| `excessive_descent_rate` | Trajectory |
| `unstable_approach` | Trajectory |
| `autopilot_disconnect` | Avionics |
| `structural_load_spike` | Structural |
| `compound_pitot_gps` | Compound |
| `compound_control_turb` | Compound |
| `compound_approach` | Compound |
| `compound_engine_fuel` | Compound |

Custom missions: use the sidebar **Custom mission** toggle and pick any mode with a start time.
