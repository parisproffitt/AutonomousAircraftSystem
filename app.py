from __future__ import annotations

import streamlit as st
import plotly.express as px

from autoflight.sim.mission import MissionConfig, run_mission
from autoflight.sim.failure_injection import FailureConfig
from autoflight.detect.rules import detect_incidents
from autoflight.detect.anomaly_ml import MLConfig, score_anomaly_risk
from autoflight.decide.policy_engine import decide


st.set_page_config(page_title="Autonomous Flight Lab — Streamlit", layout="wide")
st.title("Autonomous Flight Lab — Mission Scenarios")
st.caption("AI-driven flight failure detection and recovery with explainable outputs.")

with st.sidebar:
    st.header("Scenario Controls")
    duration_s = st.slider("Mission duration (seconds)", 120, 900, 300, 30)
    seed = st.number_input("Random seed", min_value=0, max_value=10_000, value=7, step=1)
    noise = st.slider("Noise level", 0.0, 0.5, 0.05, 0.01)
    base_turb = st.slider("Base turbulence", 0.0, 1.0, 0.10, 0.05)

    st.divider()
    st.subheader("Failure Injection")
    failure_type = st.selectbox(
        "Failure type",
        ["none", "pitot_drift", "control_degradation", "turbulence_burst"],
    )
    failure_start = st.slider("Failure start time (s)", 0, duration_s, min(90, duration_s), 5)
    drift_rate = st.slider("Pitot drift rate (kt/s)", 0.0, 0.2, 0.03, 0.01)
    control_eff = st.slider("Control effectiveness after failure", 0.2, 1.0, 0.60, 0.05)
    burst_intensity = st.slider("Turbulence burst intensity", 0.0, 1.0, 0.60, 0.05)
    burst_duration = st.slider("Turbulence burst duration (s)", 5, 120, 20, 5)

    st.divider()
    st.subheader("ML Risk Scoring (Optional)")
    enable_ml = st.checkbox("Enable ML anomaly risk scoring", value=True)
    ml_train_window = st.slider("ML training window (seconds)", 20, min(180, duration_s), 60, 10)
    ml_contamination = st.slider("Expected anomaly proportion", 0.01, 0.10, 0.03, 0.01)
    ml_risk_threshold = st.slider("Risk threshold (escalation)", 0.10, 0.95, 0.65, 0.05)

    run_btn = st.button("Run Mission", type="primary")


def build_failure():
    if failure_type == "none":
        return None
    if failure_type == "pitot_drift":
        return FailureConfig(
            name="pitot_drift",
            start_t=float(failure_start),
            params={"drift_rate": float(drift_rate)},
        )
    if failure_type == "control_degradation":
        return FailureConfig(
            name="control_degradation",
            start_t=float(failure_start),
            params={"effectiveness": float(control_eff)},
        )
    if failure_type == "turbulence_burst":
        return FailureConfig(
            name="turbulence_burst",
            start_t=float(failure_start),
            params={"intensity": float(burst_intensity), "duration": float(burst_duration)},
        )
    return None


if run_btn:
    cfg = MissionConfig(
        duration_s=int(duration_s),
        seed=int(seed),
        noise_std=float(noise),
        base_turbulence=float(base_turb),
    )
    failure = build_failure()
    df = run_mission(cfg, failure=failure)

    incidents = detect_incidents(df)

    ml_peak = None
    if enable_ml:
        ml_cfg = MLConfig(
            train_window_s=int(ml_train_window),
            contamination=float(ml_contamination),
            random_state=int(seed),
            risk_threshold=float(ml_risk_threshold),
        )
        ml_risk, _ = score_anomaly_risk(df, ml_cfg)
        df["ml_risk"] = ml_risk
        ml_peak = float(ml_risk.max())

    decision = decide(
        incidents,
        ml_risk_peak=ml_peak,
        ml_risk_threshold=float(ml_risk_threshold) if enable_ml else None,
    )

    c1, c2, c3 = st.columns([1, 1, 2])
    c1.metric("Safety State", decision.safety_state)
    c2.metric("Recommended Action", decision.action)
    c3.write("**Explanation**")
    c3.write(decision.explanation)
    if enable_ml and ml_peak is not None:
        st.caption(f"ML peak risk: `{ml_peak:.2f}` (threshold `{ml_risk_threshold:.2f}`)")

    st.divider()
    left, right = st.columns([2, 1])

    with left:
        st.subheader("Telemetry")
        fig1 = px.line(df, x="t", y=["altitude_ft"], title="Altitude (ft)")
        st.plotly_chart(fig1, use_container_width=True)

        fig2 = px.line(df, x="t", y=["airspeed_true", "airspeed_meas"], title="Airspeed (kt) — True vs Measured")
        st.plotly_chart(fig2, use_container_width=True)

        fig3 = px.line(df, x="t", y=["roll_deg"], title="Roll (deg)")
        st.plotly_chart(fig3, use_container_width=True)

        if enable_ml and "ml_risk" in df.columns:
            fig4 = px.line(df, x="t", y=["ml_risk"], title="ML Anomaly Risk Score (0–1)")
            df_thresh = df[["t"]].copy()
            df_thresh["risk_threshold"] = float(ml_risk_threshold)
            fig4.add_scatter(x=df_thresh["t"], y=df_thresh["risk_threshold"], mode="lines", name="threshold")
            st.plotly_chart(fig4, use_container_width=True)

    with right:
        st.subheader("Detected Incidents")
        if incidents:
            st.dataframe(
                [{"t": i.t, "severity": i.severity, "code": i.code, "message": i.message} for i in incidents],
                use_container_width=True,
            )
        else:
            st.write("No incidents detected.")

        st.divider()
        st.subheader("Export (JSON for Unity / Streamlit replay)")
        st.json(df.to_dict(orient="records"))

else:
    st.info("Set scenario controls on the left, then click **Run Mission**.")
