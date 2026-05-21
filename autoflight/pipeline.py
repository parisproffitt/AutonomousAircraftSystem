"""End-to-end mission assurance pipeline – sim → detect → diagnose → decide → report."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd

from autoflight.decide.policy_engine import Decision, decide
from autoflight.detect.anomaly_ml import MLConfig, score_anomaly_risk
from autoflight.detect.rules import Incident, detect_incidents
from autoflight.diagnose.root_cause import diagnose
from autoflight.explain.reporter import build_incident_report
from autoflight.scenarios.presets import ScenarioPreset
from autoflight.sim.failure_injection import FailureConfig
from autoflight.sim.mission_simulator import MissionConfig, run_mission


@dataclass
class MissionResult:
    df: pd.DataFrame
    incidents: List[Incident]
    decision: Decision
    hypotheses: List[Dict[str, str]]
    report: Dict[str, Any]
    ml_risk: Optional[pd.Series] = None
    ml_peak: Optional[float] = None


def run_pipeline(
    mission: MissionConfig,
    failures: Optional[List[FailureConfig]] = None,
    scenario_name: str = "custom",
    scenario_meta: Optional[Dict[str, Any]] = None,
    enable_ml: bool = True,
    ml_config: Optional[MLConfig] = None,
) -> MissionResult:
    """Run sim → detect → diagnose → decide → report for one mission."""
    df = run_mission(mission, failures=failures or [])
    incidents = detect_incidents(df)

    ml_risk = None
    ml_peak = None
    ml_cfg = ml_config or MLConfig(random_state=mission.seed)

    if enable_ml:
        ml_risk, _ = score_anomaly_risk(df, ml_cfg)
        df = df.copy()
        df["ml_risk"] = ml_risk
        ml_peak = float(ml_risk.max())

    decision = decide(
        df,
        incidents,
        ml_risk_peak=ml_peak,
        ml_risk_threshold=ml_cfg.risk_threshold if enable_ml else None,
    )
    hypotheses = diagnose(incidents)
    report = build_incident_report(
        scenario_name=scenario_name,
        scenario_meta=scenario_meta or {},
        df=df,
        incidents=incidents,
        decision=decision,
        hypotheses=hypotheses,
        ml_peak=ml_peak,
    )

    return MissionResult(
        df=df,
        incidents=incidents,
        decision=decision,
        hypotheses=hypotheses,
        report=report,
        ml_risk=ml_risk,
        ml_peak=ml_peak,
    )


def run_scenario(preset: ScenarioPreset, enable_ml: bool = True, ml_config: Optional[MLConfig] = None) -> MissionResult:
    return run_pipeline(
        mission=preset.mission,
        failures=preset.failures,
        scenario_name=preset.name,
        scenario_meta={"id": preset.id, "description": preset.description, "tags": preset.tags},
        enable_ml=enable_ml,
        ml_config=ml_config,
    )
