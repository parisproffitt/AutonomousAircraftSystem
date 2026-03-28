from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from autoflight.detect.rules import Incident


@dataclass(frozen=True)
class Decision:
    safety_state: str  # "NOMINAL" | "DEGRADED" | "CRITICAL"
    action: str        # "CONTINUE" | "STABILIZE" | "REROUTE" | "ABORT"
    explanation: str


def decide(
    incidents: List[Incident],
    ml_risk_peak: Optional[float] = None,
    ml_risk_threshold: Optional[float] = None,
) -> Decision:
    """
    v0.2 policy: deterministic, conservative, explainable.
    ML is used only as an escalation signal (attention / early warning),
    never as the sole basis for mission-abort.
    """
    # No incidents and no ML signal -> nominal
    if not incidents and (ml_risk_peak is None or ml_risk_threshold is None or ml_risk_peak < ml_risk_threshold):
        return Decision(
            safety_state="NOMINAL",
            action="CONTINUE",
            explanation="No envelope violations or anomaly indicators detected in telemetry.",
        )

    # If any critical rule triggers -> abort (rules are authority)
    has_critical = any(i.severity == "CRITICAL" for i in incidents)
    if has_critical:
        critical = [i for i in incidents if i.severity == "CRITICAL"][0]
        return Decision(
            safety_state="CRITICAL",
            action="ABORT",
            explanation=(
                f"Critical safety condition detected ({critical.code}) at t={critical.t:.0f}s: {critical.message} "
                f"Recommended action: ABORT to prioritize safety."
            ),
        )

    # If degraded incident exists -> stabilize
    if incidents:
        top = incidents[0]
        return Decision(
            safety_state="DEGRADED",
            action="STABILIZE",
            explanation=(
                f"Degraded condition detected ({top.code}) at t={top.t:.0f}s: {top.message} "
                f"Recommended action: STABILIZE to regain controlled, steady flight and reassess."
            ),
        )

    # ML-only escalation (no explicit rule triggered)
    # Keep it conservative but NOT catastrophic
    return Decision(
        safety_state="DEGRADED",
        action="STABILIZE",
        explanation=(
            f"Elevated anomaly risk detected by ML scoring (peak risk={ml_risk_peak:.2f} >= threshold={ml_risk_threshold:.2f}). "
            f"No rule-based envelope violations triggered, so the autonomy stack recommends STABILIZE and increased monitoring."
        ),
    )