"""Human-readable explanations and downloadable incident reports."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

from autoflight.decide.policy_engine import Decision
from autoflight.detect.rules import Incident


def explain_incident(inc: Incident) -> str:
    return (
        f"[{inc.severity}] {inc.code} ({inc.subsystem}) @ t={inc.t:.0f}s: {inc.message}"
    )


def explain_decision(decision: Decision) -> str:
    lines = [
        f"Safety State: {decision.safety_state}",
        f"Primary Action: {decision.action}",
        f"Ranked Actions: {', '.join(decision.ranked_actions)}",
        f"Confidence: {decision.confidence}",
        f"Rationale: {decision.explanation}",
    ]
    if decision.human_factors_note:
        lines.append(f"Human Factors: {decision.human_factors_note}")
    return "\n".join(lines)


def build_incident_report(
    scenario_name: str,
    scenario_meta: Dict[str, Any],
    df: pd.DataFrame,
    incidents: List[Incident],
    decision: Decision,
    hypotheses: Optional[List[Dict[str, str]]] = None,
    ml_peak: Optional[float] = None,
) -> Dict[str, Any]:
    """Build JSON-serializable incident report for download."""
    return {
        "report_version": "1.0",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "disclaimer": "SIMULATED NON-OPERATIONAL PROTOTYPE – NOT FOR FLIGHT USE",
        "scenario": scenario_name,
        "scenario_config": scenario_meta,
        "mission_summary": {
            "duration_s": float(df["t"].iloc[-1]),
            "altitude_min_ft": float(df["altitude_ft"].min()),
            "altitude_max_ft": float(df["altitude_ft"].max()),
            "peak_ml_risk": ml_peak,
        },
        "safety_state": decision.safety_state,
        "recommended_action": decision.action,
        "ranked_actions": decision.ranked_actions,
        "explanation": decision.explanation,
        "incidents": [
            {"t": i.t, "severity": i.severity, "code": i.code, "subsystem": i.subsystem, "message": i.message}
            for i in incidents
        ],
        "incident_explanations": [explain_incident(i) for i in incidents],
        "root_cause_hypotheses": hypotheses or [],
        "decision_narrative": explain_decision(decision),
    }


def report_to_markdown(report: Dict[str, Any]) -> str:
    """Render incident report as Markdown."""
    lines = [
        f"# Incident Report – {report['scenario']}",
        "",
        f"**Generated:** {report['generated_utc']}",
        "",
        f"> {report['disclaimer']}",
        "",
        "## Mission Summary",
        f"- Duration: {report['mission_summary']['duration_s']:.0f} s",
        f"- Altitude: {report['mission_summary']['altitude_min_ft']:.0f} – {report['mission_summary']['altitude_max_ft']:.0f} ft",
    ]
    if report["mission_summary"].get("peak_ml_risk") is not None:
        lines.append(f"- Peak ML risk: {report['mission_summary']['peak_ml_risk']:.3f}")

    lines.extend([
        "",
        "## Safety Decision",
        f"- **State:** {report['safety_state']}",
        f"- **Action:** {report['recommended_action']}",
        f"- **Ranked:** {', '.join(report['ranked_actions'])}",
        "",
        report["explanation"],
        "",
        "## Incidents",
    ])
    for ex in report.get("incident_explanations", []):
        lines.append(f"- {ex}")
    if not report.get("incident_explanations"):
        lines.append("- None detected")

    lines.append("\n## Root Cause Hypotheses")
    for h in report.get("root_cause_hypotheses", []):
        lines.append(f"- `{h['likely_failure']}` ({h['confidence']}) – {h['rationale']}")

    return "\n".join(lines)


def report_to_json_bytes(report: Dict[str, Any]) -> bytes:
    return json.dumps(report, indent=2).encode("utf-8")
