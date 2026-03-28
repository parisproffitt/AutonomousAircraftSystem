from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

import pandas as pd

from autoflight.detect.rules import Incident
from autoflight.decide.policy_engine import Decision


def write_markdown_report(
    out_dir: str,
    scenario: Dict[str, Any],
    df: pd.DataFrame,
    incidents: List[Incident],
    decision: Decision,
) -> str:
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    name = scenario.get("name", "scenario")
    path = Path(out_dir) / f"{ts}_{name}.md"

    lines = []
    lines.append(f"# Autonomous Flight Incident Report — {name}")
    lines.append("")
    lines.append(f"Generated: {datetime.now().isoformat(timespec='seconds')}")
    lines.append("")
    lines.append("## Scenario Configuration")
    for k, v in scenario.items():
        lines.append(f"- **{k}**: `{v}`")
    lines.append("")
    lines.append("## Decision")
    lines.append(f"- **Safety State**: `{decision.safety_state}`")
    lines.append(f"- **Recommended Action**: `{decision.action}`")
    lines.append(f"- **Explanation**: {decision.explanation}")
    lines.append("")
    lines.append("## Detected Incidents")
    if not incidents:
        lines.append("- None")
    else:
        for inc in incidents:
            lines.append(f"- t={inc.t:.0f}s | **{inc.severity}** | `{inc.code}` — {inc.message}")
    lines.append("")
    lines.append("## Telemetry Summary")
    lines.append(f"- Duration: `{df['t'].iloc[-1]:.0f}s`")
    lines.append(f"- Altitude range: `{df['altitude_ft'].min():.0f}–{df['altitude_ft'].max():.0f} ft`")
    lines.append(f"- Airspeed true range: `{df['airspeed_true'].min():.0f}–{df['airspeed_true'].max():.0f} kt`")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)