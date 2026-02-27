import streamlit as st
import plotly.express as px

from sentinel.sim.mission import MissionConfig, run_mission
from sentinel.sim.failure_injection import FailureConfig
from sentinel.detect.rules import detect_incidents
from sentinel.detect.anomaly_ml import MLConfig, score_anomaly_risk
from sentinel.decide.policy_engine import decide
from sentinel.explain.reporter import write_markdown_report


st.set_page_config(page_title="Sentinel Scenario Lab", layout="wide")

st.title("Sentinel — Interactive Scenario Lab")
st.caption(
    "Simulated telemetry + decision-level anomaly detection + explainable recovery recommendations (research prototype)."
)

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

    # Train on first N seconds (assumed nominal-ish)
    ml_train_window = st.slider(
        "ML training window (seconds)",
        20,
        min(180, duration_s),
        60,
        10,
    )
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
    # 1) Run mission sim
    cfg = MissionConfig(
        duration_s=int(duration_s),
        seed=int(seed),
        noise_std=float(noise),
        base_turbulence=float(base_turb),
    )
    failure = build_failure()
    df = run_mission(cfg, failure=failure)

    # 2) Rule-based detection
    incidents = detect_incidents(df)

    # 3) ML risk scoring 
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

    # 4) Decision (rules are primary; ML only escalates if no rules fired)
    decision = decide(
        incidents,
        ml_risk_peak=ml_peak,
        ml_risk_threshold=float(ml_risk_threshold) if enable_ml else None,
    )

    # ===== Top summary =====
    c1, c2, c3 = st.columns([1, 1, 2])
    c1.metric("Safety State", decision.safety_state)
    c2.metric("Recommended Action", decision.action)
    c3.write("**Explanation**")
    c3.write(decision.explanation)

    if enable_ml:
        st.caption(f"ML peak risk: `{ml_peak:.2f}` (threshold `{ml_risk_threshold:.2f}`)")  # safe even if no incidents

    st.divider()

    left, right = st.columns([2, 1])

    # ===== Telemetry plots =====
    with left:
        st.subheader("Telemetry")

        fig1 = px.line(df, x="t", y=["altitude_ft"], title="Altitude (ft)")
        st.plotly_chart(fig1, use_container_width=True)

        fig2 = px.line(df, x="t", y=["airspeed_true", "airspeed_meas"], title="Airspeed (kt) — True vs Measured")
        st.plotly_chart(fig2, use_container_width=True)

        fig3 = px.line(df, x="t", y=["roll_deg"], title="Roll (deg)")
        st.plotly_chart(fig3, use_container_width=True)

        # ML risk curve + threshold line
        if enable_ml and "ml_risk" in df.columns:
            fig4 = px.line(df, x="t", y=["ml_risk"], title="ML Anomaly Risk Score (0–1)")

            # Threshold line as a second trace
            df_thresh = df[["t"]].copy()
            df_thresh["risk_threshold"] = float(ml_risk_threshold)
            fig4.add_scatter(
                x=df_thresh["t"],
                y=df_thresh["risk_threshold"],
                mode="lines",
                name="threshold",
            )

            st.plotly_chart(fig4, use_container_width=True)

    # ===== Incidents + report export =====
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
        st.subheader("Export Report")

        scenario_meta = {
            "name": failure_type if failure_type != "none" else "nominal",
            "duration_s": duration_s,
            "seed": seed,
            "noise": noise,
            "base_turbulence": base_turb,
            "failure_type": failure_type,
            "failure_start_s": failure_start,
            "drift_rate": drift_rate,
            "control_effectiveness": control_eff,
            "burst_intensity": burst_intensity,
            "burst_duration": burst_duration,
            "enable_ml": enable_ml,
            "ml_train_window_s": ml_train_window,
            "ml_contamination": ml_contamination,
            "ml_risk_threshold": ml_risk_threshold,
            "ml_risk_peak": ml_peak,
        }

        report_path = write_markdown_report(
            out_dir="reports",
            scenario=scenario_meta,
            df=df,
            incidents=incidents,
            decision=decision,
        )

        with open(report_path, "r", encoding="utf-8") as f:
            st.download_button(
                label="Download incident report (Markdown)",
                data=f.read(),
                file_name=report_path.split("/")[-1],
                mime="text/markdown",
            )

else:
    st.info("Set scenario controls on the left, then click **Run Mission**.")