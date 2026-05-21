"""Safety state machine – NOMINAL → DEGRADED → CRITICAL → EMERGENCY."""

from __future__ import annotations

from enum import Enum
from typing import List

from autoflight.detect.rules import Incident


class SafetyState(str, Enum):
    NOMINAL = "NOMINAL"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"


class RecoveryAction(str, Enum):
    CONTINUE = "CONTINUE"
    STABILIZE = "STABILIZE"
    REROUTE = "REROUTE"
    ABORT = "ABORT"
    EMERGENCY_DESCENT = "EMERGENCY_DESCENT"
    SAFE_TERMINATION = "SAFE_TERMINATION"


# Severity ordering for state aggregation
_SEVERITY_RANK = {"DEGRADED": 1, "CRITICAL": 2, "EMERGENCY": 3}


def aggregate_safety_state(incidents: List[Incident], ml_elevated: bool) -> SafetyState:
    """Classify overall safety state from incidents and ML escalation flag."""
    if not incidents and not ml_elevated:
        return SafetyState.NOMINAL

    max_sev = 0
    for inc in incidents:
        max_sev = max(max_sev, _SEVERITY_RANK.get(inc.severity, 1))

    emergency_codes = {"LOW_ALT_HIGH_DESCENT", "STRUCTURAL_MARGIN_LOW", "HIGH_G_LOAD"}
    if any(i.code in emergency_codes and i.severity == "CRITICAL" for i in incidents):
        return SafetyState.EMERGENCY

    if max_sev >= 2:
        return SafetyState.CRITICAL
    if max_sev >= 1 or ml_elevated:
        return SafetyState.DEGRADED
    return SafetyState.NOMINAL
