"""Recovery decision policy – ranks actions using severity, constraints, and proxies."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd

from autoflight.decide.state_machine import RecoveryAction, SafetyState, aggregate_safety_state
from autoflight.detect.rules import Incident


@dataclass(frozen=True)
class Decision:
    safety_state: str
    action: str
    explanation: str
    ranked_actions: List[str] = field(default_factory=list)
    confidence: str = "HIGH"
    human_factors_note: str = ""


def _mission_constraints(df: pd.DataFrame) -> dict[str, float]:
    """Extract constraint proxies from latest telemetry."""
    last = df.iloc[-1]
    return {
        "fuel_pct": float(last.get("fuel_remaining_pct", 50)),
        "structural_margin": float(last.get("structural_margin_proxy", 0.8)),
        "altitude_ft": float(last.get("altitude_ft", 5000)),
        "control_eff": float(last.get("control_effectiveness", 1.0)),
        "approach_stability": float(last.get("approach_stability_index", 0.9)),
    }


def _rank_actions(
    state: SafetyState,
    incidents: List[Incident],
    constraints: dict[str, float],
) -> List[str]:
    """Rank recovery actions by severity and mission constraints."""
    fuel_low = constraints["fuel_pct"] < 20
    low_alt = constraints["altitude_ft"] < 2500
    poor_control = constraints["control_eff"] < 0.55
    unstable = constraints["approach_stability"] < 0.45

    if state == SafetyState.NOMINAL:
        return [RecoveryAction.CONTINUE.value]

    if state == SafetyState.EMERGENCY:
        order = [RecoveryAction.EMERGENCY_DESCENT, RecoveryAction.SAFE_TERMINATION, RecoveryAction.ABORT]
        return [a.value for a in order]

    if state == SafetyState.CRITICAL:
        order = [RecoveryAction.ABORT, RecoveryAction.SAFE_TERMINATION, RecoveryAction.EMERGENCY_DESCENT]
        if unstable and not fuel_low:
            order = [RecoveryAction.ABORT, RecoveryAction.REROUTE, RecoveryAction.STABILIZE]
        if poor_control and low_alt:
            order = [RecoveryAction.EMERGENCY_DESCENT, RecoveryAction.ABORT, RecoveryAction.STABILIZE]
        return [a.value for a in order]

    # DEGRADED
    order = [RecoveryAction.STABILIZE, RecoveryAction.CONTINUE, RecoveryAction.REROUTE]
    if any(i.code == "GPS_DEGRADED" for i in incidents):
        order = [RecoveryAction.REROUTE, RecoveryAction.STABILIZE, RecoveryAction.CONTINUE]
    if any(i.code in ("AIRSPEED_SENSOR_DISAGREE", "SENSOR_DISAGREEMENT") for i in incidents):
        order = [RecoveryAction.STABILIZE, RecoveryAction.REROUTE, RecoveryAction.CONTINUE]
    return [a.value for a in order]


def decide(
    df: pd.DataFrame,
    incidents: List[Incident],
    ml_risk_peak: Optional[float] = None,
    ml_risk_threshold: Optional[float] = None,
) -> Decision:
    """
    Deterministic recovery policy. Rules are authoritative for abort/emergency;
    ML only elevates monitoring priority (STABILIZE), never sole abort trigger.
    """
    ml_elevated = (
        ml_risk_peak is not None
        and ml_risk_threshold is not None
        and ml_risk_peak >= ml_risk_threshold
    )
    state = aggregate_safety_state(incidents, ml_elevated)
    constraints = _mission_constraints(df)
    ranked = _rank_actions(state, incidents, constraints)
    primary = ranked[0]

    if state == SafetyState.NOMINAL:
        return Decision(
            safety_state=state.value,
            action=primary,
            explanation=(
                "Telemetry within envelopes. No rule violations or elevated ML risk. "
                "Recommend CONTINUE."
            ),
            ranked_actions=ranked,
            confidence="HIGH",
            human_factors_note="",
        )

    if state == SafetyState.EMERGENCY:
        top = next((i for i in incidents if i.severity in ("CRITICAL", "EMERGENCY")), incidents[0] if incidents else None)
        msg = top.message if top else "Compound critical conditions"
        return Decision(
            safety_state=state.value,
            action=primary,
            explanation=(
                f"EMERGENCY safety state: {msg}. "
                f"Ranked actions: {', '.join(ranked)}. Primary: {primary} – immediate crew intervention required. "
                f"Fuel {constraints['fuel_pct']:.0f}%, altitude {constraints['altitude_ft']:.0f} ft."
            ),
            ranked_actions=ranked,
            confidence="HIGH",
            human_factors_note="Recommendations only; operator retains authority.",
        )

    if state == SafetyState.CRITICAL:
        critical = [i for i in incidents if i.severity == "CRITICAL"]
        top = critical[0] if critical else incidents[0]
        return Decision(
            safety_state=state.value,
            action=primary,
            explanation=(
                f"CRITICAL: {top.code} at t={top.t:.0f}s – {top.message} "
                f"Recommended: {primary}. Alternatives: {', '.join(ranked[1:])}. "
                f"Structural margin {constraints['structural_margin']:.2f}, fuel {constraints['fuel_pct']:.0f}%."
            ),
            ranked_actions=ranked,
            confidence="HIGH",
            human_factors_note="Simulated environment; no autonomous actuation.",
        )

    # DEGRADED (including ML-only escalation)
    if incidents:
        top = incidents[0]
        expl = (
            f"DEGRADED: {top.code} at t={top.t:.0f}s – {top.message} "
            f"Primary action {primary}; ranked {', '.join(ranked)}."
        )
    else:
        expl = (
            f"DEGRADED: ML early-warning (peak risk {ml_risk_peak:.2f} ≥ {ml_risk_threshold:.2f}). "
            f"No rule abort triggered. Recommend {primary} and increased sensor cross-check."
        )

    return Decision(
        safety_state=state.value,
        action=primary,
        explanation=expl,
        ranked_actions=ranked,
        confidence="MEDIUM" if ml_elevated and not incidents else "HIGH",
        human_factors_note="ML risk is advisory; rules drive state.",
    )
