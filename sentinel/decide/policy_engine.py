from __future__ import annotations

from dataclasses import dataclass
from typing import List

from sentinel.detect.rules import Incident


@dataclass(frozen=True)
class Decision:
    safety_state: str  # "NOMINAL" | "DEGRADED" | "CRITICAL"
    action: str        # "CONTINUE" | "STABILIZE" | "REROUTE" | "ABORT"
    explanation: str


def decide(incidents: List[Incident]) -> Decision:
    """
    v0.1 policy: conservative, explainable, deterministic.
    """
    if not incidents:
        return Decision(
            safety_state="NOMINAL",
            action="CONTINUE",
            explanation="No envelope violations or anomaly indicators detected in telemetry.",
        )

    has_critical = any(i.severity == "CRITICAL" for i in incidents)

    if has_critical:
        critical = [i for i in incidents if i.severity == "CRITICAL"][0]
        return Decision(
            safety_state="CRITICAL",
            action="ABORT",
            explanation=f"Critical safety condition detected ({critical.code}) at t={critical.t:.0f}s: {critical.message} Recommended action: ABORT to prioritize safety.",
        )

    # otherwise degraded
    top = incidents[0]
    return Decision(
        safety_state="DEGRADED",
        action="STABILIZE",
        explanation=f"Degraded condition detected ({top.code}) at t={top.t:.0f}s: {top.message} Recommended action: STABILIZE to regain controlled, steady flight and reassess.",
    )