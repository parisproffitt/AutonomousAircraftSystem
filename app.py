"""
Mission Control UI — Autonomous Flight Failure Detection & Recovery (simulated).
"""

from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from autoflight.detect.anomaly_ml import MLConfig
from autoflight.explain.reporter import explain_incident, report_to_json_bytes, report_to_markdown
from autoflight.pipeline import run_pipeline, run_scenario
from autoflight.scenarios.presets import PRESET_SCENARIOS, list_scenarios
from autoflight.sim.failure_injection import FailureConfig, list_failure_modes
from autoflight.sim.mission_simulator import MissionConfig

st.set_page_config(
    page_title="Autonomous Flight Failure Detection & Recovery",
    layout="wide",
    initial_sidebar_state="expanded",
)

STATE_COLORS = {
    "NOMINAL": ("#22c55e", "●"),
    "DEGRADED": ("#eab308", "●"),
    "CRITICAL": ("#f97316", "●"),
    "EMERGENCY": ("#ef4444", "●"),
}

PLOTLY_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(17,27,46,0.6)",
    font=dict(family="system-ui, sans-serif", color="#94a3b8", size=11),
    margin=dict(l=48, r=24, t=40, b=36),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
)

st.markdown(
    """
    <style>
    #MainMenu, footer { visibility: hidden; }
    header[data-testid="stHeader"] { background: transparent; }
    .block-container { padding-top: 1.2rem; max-width: 1400px; }
    .mc-title {
        font-size: 1.35rem; font-weight: 700; letter-spacing: -0.02em; color: #e2e8f0;
    }
    .mc-subtitle { color: #64748b; font-size: 0.88rem; margin-top: 0.2rem; }
    .hud-card {
        background: linear-gradient(145deg, #111b2e 0%, #0f172a 100%);
        border: 1px solid #1e293b; border-radius: 12px;
        padding: 1rem 1.1rem; min-height: 88px;
    }
    .hud-label { color: #64748b; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.08em; }
    .hud-value { font-size: 1.55rem; font-weight: 700; color: #f1f5f9; margin-top: 0.15rem; }
    .footer-note { color: #475569; font-size: 0.75rem; text-align: center; padding: 1rem 0 0.5rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

if "selected_scenario" not in st.session_state:
    st.session_state.selected_scenario = "nominal_mission"
if "last_result" not in st.session_state:
    st.session_state.last_result = None


def _hud_metric(label: str, value: str, color: str = "#f1f5f9") -> str:
    return f"""
    <div class="hud-card">
        <div class="hud-label">{label}</div>
        <div class="hud-value" style="color:{color}">{value}</div>
    </div>
    """


def _apply_plotly_style(fig: go.Figure, height: int = 260) -> go.Figure:
    fig.update_layout(**PLOTLY_LAYOUT, height=height)
    fig.update_xaxes(gridcolor="#1e293b", zerolinecolor="#334155")
    fig.update_yaxes(gridcolor="#1e293b", zerolinecolor="#334155")
    return fig


def _state_timeline_fig(df, incidents, ml_threshold: float, ml_peak: float | None):
    states = []
    for _, row in df.iterrows():
        active = [i for i in incidents if abs(i.t - float(row["t"])) < 2]
        if any(i.severity == "CRITICAL" for i in active):
            states.append("CRITICAL")
        elif any(i.severity == "EMERGENCY" for i in active):
            states.append("EMERGENCY")
        elif active or (
            ml_peak and "ml_risk" in df.columns and float(row.get("ml_risk", 0)) >= ml_threshold
        ):
            states.append("DEGRADED")
        else:
            states.append("NOMINAL")

    order = ["NOMINAL", "DEGRADED", "CRITICAL", "EMERGENCY"]
    y_map = {s: i for i, s in enumerate(order)}
    colors = [STATE_COLORS[s][0] for s in states]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["t"],
            y=[y_map[s] for s in states],
            mode="markers",
            marker=dict(size=9, color=colors, line=dict(width=1, color="#0f172a")),
            text=states,
            hovertemplate="t=%{x:.0f}s<br>state=%{text}<extra></extra>",
        )
    )
    fig.update_yaxes(tickvals=list(y_map.values()), ticktext=order, range=[-0.5, 3.5], title="")
    fig.update_layout(title="Safety State Timeline", **PLOTLY_LAYOUT, height=220)
    return fig


st.markdown('<div class="mc-title">Autonomous Flight Failure Detection & Recovery</div>', unsafe_allow_html=True)
st.markdown('<div class="mc-subtitle">Mission Control · simulated telemetry · non-operational</div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### Mission config")

    presets = list_scenarios()
    preset_ids = [p.id for p in presets]
    labels = {p.id: p.name for p in presets}

    selected = st.selectbox(
        "Scenario",
        preset_ids,
        index=preset_ids.index(st.session_state.selected_scenario),
        format_func=lambda x: labels[x],
    )
    st.session_state.selected_scenario = selected
    preset = PRESET_SCENARIOS[selected]
    st.caption(preset.description)

    custom_mode = st.toggle("Custom mission", value=False)

    if custom_mode:
        duration_s = st.slider("Duration (s)", 120, 600, 300, 30)
        seed = st.number_input("Seed", 0, 9999, 7)
        noise = st.slider("Noise", 0.0, 0.15, 0.04, 0.01)
        turb = st.slider("Turbulence", 0.0, 0.3, 0.08, 0.01)
        failure = st.selectbox("Inject failure", ["none"] + list_failure_modes())
        failure_start = st.slider("Failure start (s)", 0, duration_s, 90, 5)
    else:
        duration_s = preset.mission.duration_s
        seed = preset.mission.seed

    with st.expander("ML settings", expanded=False):
        enable_ml = st.checkbox("ML risk scoring", value=True)
        ml_train = st.slider("Train window (s)", 20, 120, 60, 10)
        ml_contamination = st.slider("Anomaly rate", 0.01, 0.12, 0.04, 0.01)
        ml_threshold = st.slider("Escalation threshold", 0.3, 0.95, 0.65, 0.05)

    run_btn = st.button("Run mission", type="primary", use_container_width=True)
    st.caption("Simulated prototype. No aircraft integration.")

st.markdown("##### Scenarios")
preset_cols = st.columns(3)
for i, p in enumerate(presets):
    with preset_cols[i % 3]:
        if st.button(
            p.name,
            key=f"preset_{p.id}",
            use_container_width=True,
            type="primary" if st.session_state.selected_scenario == p.id else "secondary",
        ):
            st.session_state.selected_scenario = p.id
            st.rerun()

st.divider()

if run_btn:
    ml_cfg = MLConfig(
        train_window_s=ml_train,
        contamination=ml_contamination,
        risk_threshold=ml_threshold,
        random_state=int(seed),
    )

    with st.spinner("Running pipeline…"):
        if custom_mode:
            mission = MissionConfig(
                duration_s=int(duration_s),
                seed=int(seed),
                noise_std=float(noise),
                base_turbulence=float(turb),
            )
            failures = []
            if failure != "none":
                failures = [FailureConfig(name=failure, start_t=float(failure_start))]
            result = run_pipeline(
                mission,
                failures=failures,
                scenario_name=failure,
                scenario_meta={"failure": failure},
                enable_ml=enable_ml,
                ml_config=ml_cfg,
            )
        else:
            result = run_scenario(preset, enable_ml=enable_ml, ml_config=ml_cfg)

    st.session_state.last_result = result
    st.session_state.ml_threshold = ml_threshold
    st.session_state.enable_ml = enable_ml

if st.session_state.last_result is not None:
    result = st.session_state.last_result
    decision = result.decision
    df = result.df
    incidents = result.incidents
    ml_threshold = st.session_state.get("ml_threshold", 0.65)
    enable_ml = st.session_state.get("enable_ml", True)
    state_color = STATE_COLORS.get(decision.safety_state, ("#94a3b8", "●"))[0]

    h1, h2, h3, h4 = st.columns(4)
    with h1:
        st.markdown(_hud_metric("Safety State", decision.safety_state, state_color), unsafe_allow_html=True)
    with h2:
        st.markdown(_hud_metric("Primary Action", decision.action, "#38bdf8"), unsafe_allow_html=True)
    with h3:
        st.markdown(_hud_metric("Incidents", str(len(incidents)), "#f97316" if incidents else "#22c55e"), unsafe_allow_html=True)
    with h4:
        risk_txt = f"{result.ml_peak:.2f}" if result.ml_peak is not None else "—"
        risk_col = "#ef4444" if result.ml_peak and result.ml_peak >= ml_threshold else "#94a3b8"
        st.markdown(_hud_metric("Peak ML Risk", risk_txt, risk_col), unsafe_allow_html=True)

    st.markdown("**Rationale**")
    st.info(decision.explanation)
    if decision.ranked_actions:
        st.caption("Ranked: " + " → ".join(decision.ranked_actions))

    left, right = st.columns([1.35, 1])

    with left:
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=("Altitude (ft)", "Airspeed (kt)", "Attitude (°)", "ML Risk"),
            vertical_spacing=0.14,
            horizontal_spacing=0.08,
        )
        fig.add_trace(go.Scatter(x=df["t"], y=df["altitude_ft"], name="Alt", line=dict(color="#38bdf8")), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["t"], y=df["airspeed_true_kt"], name="True", line=dict(color="#22c55e")), row=1, col=2)
        fig.add_trace(go.Scatter(x=df["t"], y=df["airspeed_meas_kt"], name="Meas", line=dict(color="#f97316", dash="dot")), row=1, col=2)
        fig.add_trace(go.Scatter(x=df["t"], y=df["pitch_deg"], name="Pitch", line=dict(color="#818cf8")), row=2, col=1)
        fig.add_trace(go.Scatter(x=df["t"], y=df["roll_deg"], name="Roll", line=dict(color="#c084fc")), row=2, col=1)
        if enable_ml and "ml_risk" in df.columns:
            fig.add_trace(go.Scatter(x=df["t"], y=df["ml_risk"], fill="tozeroy", name="Risk", line=dict(color="#f59e0b")), row=2, col=2)
            fig.add_hline(y=ml_threshold, line_dash="dash", line_color="#ef4444", row=2, col=2)
        st.plotly_chart(_apply_plotly_style(fig, height=480), use_container_width=True)
        st.plotly_chart(
            _apply_plotly_style(_state_timeline_fig(df, incidents, ml_threshold, result.ml_peak), 220),
            use_container_width=True,
        )

    with right:
        st.markdown("##### Incidents")
        if incidents:
            for inc in sorted(incidents, key=lambda x: x.t):
                color = STATE_COLORS.get(inc.severity, ("#94a3b8", ""))[0]
                st.markdown(
                    f'<div style="border-left:3px solid {color};padding:0.4rem 0.8rem;margin:0.35rem 0;'
                    f'background:#111b2e;border-radius:0 8px 8px 0;">'
                    f'<span style="color:{color};font-weight:600;">{inc.severity}</span> '
                    f'<code style="color:#94a3b8;">{inc.code}</code> @ {inc.t:.0f}s<br>'
                    f'<span style="color:#cbd5e1;font-size:0.85rem;">{inc.message}</span></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.success("No rule violations.")

        if result.hypotheses:
            st.markdown("##### Root cause")
            st.dataframe(result.hypotheses, use_container_width=True, hide_index=True)

        with st.expander("Telemetry summary & export"):
            st.dataframe(df.describe().T, use_container_width=True)
            md = report_to_markdown(result.report)
            st.download_button("Download JSON", report_to_json_bytes(result.report), "incident_report.json")
            st.download_button("Download Markdown", md.encode(), "incident_report.md")

else:
    st.info("Select a scenario and click **Run mission** in the sidebar.")
