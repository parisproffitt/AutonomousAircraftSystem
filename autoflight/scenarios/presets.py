"""Built-in mission presets with timed failure injection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from autoflight.sim.failure_injection import FailureConfig
from autoflight.sim.mission_simulator import MissionConfig


@dataclass(frozen=True)
class ScenarioPreset:
    id: str
    name: str
    description: str
    mission: MissionConfig
    failures: List[FailureConfig]
    tags: List[str]


def _f(name: str, start: float, **params: Any) -> FailureConfig:
    return FailureConfig(name=name, start_t=start, params=dict(params))


PRESET_SCENARIOS: Dict[str, ScenarioPreset] = {
    "nominal_mission": ScenarioPreset(
        id="nominal_mission",
        name="Nominal Mission",
        description="Climb–cruise–descent with no injected failures.",
        mission=MissionConfig(duration_s=300, seed=7, noise_std=0.03, base_turbulence=0.06),
        failures=[],
        tags=["baseline"],
    ),
    "pitot_drift": ScenarioPreset(
        id="pitot_drift",
        name="Pitot / Static Drift",
        description="Growing airspeed measurement bias (pitot icing / blockage proxy).",
        mission=MissionConfig(duration_s=300, seed=11, noise_std=0.04),
        failures=[_f("pitot_drift", 90.0, drift_rate=0.05)],
        tags=["air-data"],
    ),
    "turbulence_approach": ScenarioPreset(
        id="turbulence_approach",
        name="Turbulence During Approach",
        description="Turbulence burst during approach with roll excursions.",
        mission=MissionConfig(duration_s=300, seed=19, base_turbulence=0.12),
        failures=[_f("turbulence_burst", 230.0, intensity=0.82, duration=30.0)],
        tags=["environment", "approach"],
    ),
    "control_degradation": ScenarioPreset(
        id="control_degradation",
        name="Control Authority Degradation",
        description="Reduced control effectiveness and actuator lag.",
        mission=MissionConfig(duration_s=300, seed=23),
        failures=[
            _f("control_authority_loss", 120.0, effectiveness=0.48),
            _f("actuator_lag", 120.0, lag_ms=180),
        ],
        tags=["flight-controls"],
    ),
    "gps_degradation": ScenarioPreset(
        id="gps_degradation",
        name="GPS Degradation",
        description="Falling GPS confidence and growing position error.",
        mission=MissionConfig(duration_s=300, seed=31),
        failures=[_f("gps_degradation", 100.0, confidence_decay=0.025, error_growth=3.5)],
        tags=["navigation"],
    ),
    "compound_failure": ScenarioPreset(
        id="compound_failure",
        name="Compound Failure (Pitot + GPS)",
        description="Pitot drift combined with GPS degradation.",
        mission=MissionConfig(duration_s=300, seed=37, noise_std=0.05),
        failures=[_f("compound_pitot_gps", 85.0, drift_rate=0.04, confidence_decay=0.02)],
        tags=["compound"],
    ),
}


def get_scenario(scenario_id: str) -> Optional[ScenarioPreset]:
    return PRESET_SCENARIOS.get(scenario_id)


def list_scenarios() -> List[ScenarioPreset]:
    return list(PRESET_SCENARIOS.values())
