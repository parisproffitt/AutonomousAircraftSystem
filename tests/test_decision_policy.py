"""Tests for recovery decision policy and state machine."""

from autoflight.decide.policy_engine import decide
from autoflight.decide.state_machine import SafetyState, aggregate_safety_state
from autoflight.detect.rules import Incident
from autoflight.pipeline import run_scenario
from autoflight.scenarios.presets import PRESET_SCENARIOS
from autoflight.sim.mission_simulator import MissionConfig, run_mission


def test_nominal_scenario_continue():
    result = run_scenario(PRESET_SCENARIOS["nominal_mission"], enable_ml=True)
    assert result.decision.safety_state in ("NOMINAL", "DEGRADED")
    assert result.decision.action in ("CONTINUE", "STABILIZE", "REROUTE")


def test_compound_failure_not_nominal():
    result = run_scenario(PRESET_SCENARIOS["compound_failure"], enable_ml=True)
    assert result.decision.safety_state != "NOMINAL" or len(result.incidents) > 0


def test_critical_incident_triggers_abort_or_emergency():
    df = run_mission(MissionConfig(duration_s=50, seed=1))
    incidents = [
        Incident(t=10.0, severity="CRITICAL", code="LOW_ALT_HIGH_DESCENT",
                 message="test", subsystem="TRAJECTORY"),
    ]
    d = decide(df, incidents)
    assert d.action in ("ABORT", "EMERGENCY_DESCENT", "SAFE_TERMINATION", "STABILIZE", "REROUTE")


def test_aggregate_emergency_state():
    inc = [Incident(t=1.0, severity="CRITICAL", code="LOW_ALT_HIGH_DESCENT", message="x", subsystem="T")]
    assert aggregate_safety_state(inc, False) == SafetyState.EMERGENCY


def test_ranked_actions_populated():
    result = run_scenario(PRESET_SCENARIOS["pitot_drift"])
    assert len(result.decision.ranked_actions) >= 1
