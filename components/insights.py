"""Non-operational visual insights for the fictional SMARTSCAN simulation."""
from __future__ import annotations
from datetime import datetime
import html
from textwrap import dedent
import streamlit as st
from analytics import compute_kpis
from simulation import SCENARIOS, SECTORS, TOTAL_ROUNDS, activity_probability


def render_guided_demo() -> None:
    enabled = st.checkbox("Enable guided demo mode", key="guided_demo")
    if not enabled:
        return
    with st.container(border=True):
        st.markdown("### 🧭 Guided demonstration")
        st.caption("A presenter-friendly tour of the synthetic software prototype.")
        steps = [
            ("01 · Introduction", "Explain that SMARTSCAN AI is an educational, fictional simulation."),
            ("02 · Environment", "Introduce the five fictional sectors and the synthetic scenario selector."),
            ("03 · Mission Control", "Use Step Round or Run Live Simulation to advance the software simulation."),
            ("04 · Visual progress", "Show the compact progress panel and the recorded-observation heatmap."),
            ("05 · Analytics", "Explain the metric definitions and why unsupported metrics are marked unavailable."),
            ("06 · Experiment history", "Save a snapshot and compare it with other runs in this browser session."),
        ]
        for title, description in steps:
            st.markdown(f"**{title}**  \n{description}")


def _heatmap_html(sim, max_rounds: int = 24) -> str:
    recent_rounds = list(range(max(1, sim.round - max_rounds + 1), sim.round + 1))
    if not recent_rounds:
        recent_rounds = [1]
    observed = {(h["selected"], h["round"]): bool(h["detected"]) for h in sim.history}
    head = "".join(f"<th>R{r}</th>" for r in recent_rounds)
    rows = []
    for sector in SECTORS:
        cells = []
        for rnd in recent_rounds:
            value = observed.get((sector.name, rnd), None)
            if value is True:
                css, label = "active", "Active"
            elif value is False:
                css, label = "idle", "Inactive"
            else:
                css, label = "unknown", "Not observed"
            cells.append(f'<td class="{css}" title="{sector.name}, round {rnd}: {label}"></td>')
        rows.append(f'<tr><th>{html.escape(sector.name)}</th>{"".join(cells)}</tr>')
    return (
        '<div class="ss-insight-table-wrap"><table class="ss-heatmap">'
        f'<thead><tr><th>Sector</th>{head}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>'
    )


def _scenario_profile(scenario: str) -> list[dict]:
    profile = []
    for sector in SECTORS:
        mean_probability = sum(
            activity_probability(sector, scenario, rnd)
            for rnd in range(1, TOTAL_ROUNDS + 1)
        ) / TOTAL_ROUNDS
        profile.append({
            "Sector": sector.name,
            "Expected synthetic activity": round(mean_probability * 100, 1),
        })
    return profile


def render_insights(sim) -> None:
    st.markdown("### 📊 Simulation insights")
    left, right = st.columns([1.25, 1])
    with left:
        st.markdown("**B1 · Recorded-observation heatmap**")
        st.caption("Only recorded observations are coloured. Blank cells mean the sector was not observed in that round.")
        st.markdown(_heatmap_html(sim), unsafe_allow_html=True)
        st.markdown(
            '<div class="ss-heat-legend"><span><i class="active"></i> Active</span>'
            '<span><i class="idle"></i> Inactive</span>'
            '<span><i class="unknown"></i> Not observed</span></div>',
            unsafe_allow_html=True,
        )
    with right:
        st.markdown("**B4 · Explainable event summary**")
        if sim.last_events:
            event = sim.last_events[-1]
            status = "ACTIVE" if event["detected"] else "INACTIVE"
            st.metric("Latest recorded sector", event["sector"])
            st.metric("Simulation round", f'{event["round"]} / {TOTAL_ROUNDS}')
            st.info(
                f"Synthetic environment label: **{status}**. "
                f"The recorded reward change was **{event['reward']:+d} points**."
            )
            st.caption("This describes a fictional simulation event, not a real-world recommendation.")
        else:
            st.info("Advance the simulation to display an explanation of the latest synthetic event.")

    st.markdown("**B2 · Synthetic scenario reference comparison**")
    st.caption("Compares expected synthetic activity profiles, not scheduler performance. The stationary scenario is the reference profile.")
    selected = st.session_state.get("scenario", "dynamic_surge")
    base = _scenario_profile("stationary")
    chosen = _scenario_profile(selected)
    comparison_rows = []
    for base_row, chosen_row in zip(base, chosen):
        sector_name = html.escape(base_row["Sector"])
        base_value = float(base_row["Expected synthetic activity"])
        chosen_value = float(chosen_row["Expected synthetic activity"])
        base_width = max(0.0, min(100.0, base_value))
        chosen_width = max(0.0, min(100.0, chosen_value))
        comparison_rows.append(
            dedent(f"""
            <div class="ss-compare-row">
              <div class="ss-compare-sector">{sector_name}</div>
              <div class="ss-compare-bars">
                <div class="ss-compare-line">
                  <span class="ss-compare-label">Stationary</span>
                  <div class="ss-compare-track"><div class="ss-compare-fill ss-compare-base" style="width:{base_width}%"></div></div>
                  <span class="ss-compare-value">{base_value:.1f}%</span>
                </div>
                <div class="ss-compare-line">
                  <span class="ss-compare-label">{html.escape(SCENARIOS[selected])}</span>
                  <div class="ss-compare-track"><div class="ss-compare-fill ss-compare-selected" style="width:{chosen_width}%"></div></div>
                  <span class="ss-compare-value">{chosen_value:.1f}%</span>
                </div>
              </div>
            </div>
            """).strip()
        )
    st.markdown(
        '<div class="ss-scenario-comparison">'
        + "".join(comparison_rows)
        + '</div>',
        unsafe_allow_html=True,
    )

    st.markdown("**C4 · Experiment history**")
    if "experiment_history" not in st.session_state:
        st.session_state.experiment_history = []
    if st.button("＋ Save current experiment snapshot", key="save_experiment", disabled=sim.round == 0):
        kpis = compute_kpis(sim)
        record = {
            "Experiment": len(st.session_state.experiment_history) + 1,
            "Saved at": datetime.now().strftime("%H:%M:%S"),
            "Scenario": SCENARIOS.get(selected, selected),
            "Rounds": sim.round,
            "Synthetic Pd": kpis["pd"],
            "Active yield": kpis["observed_yield"],
            "Avg reward": kpis["avg_reward"],
        }
        st.session_state.experiment_history.append(record)
        st.success("Experiment snapshot saved for this session.")
    if st.session_state.experiment_history:
        columns = ["Experiment", "Saved at", "Scenario", "Rounds", "Synthetic Pd", "Active yield", "Avg reward"]
        header = "".join(f"<th>{html.escape(column)}</th>" for column in columns)
        body_rows = []
        for record in st.session_state.experiment_history:
            cells = "".join(
                f"<td>{html.escape(str(record.get(column, '—')))}</td>"
                for column in columns
            )
            body_rows.append(f"<tr>{cells}</tr>")
        st.markdown(
            '<div class="ss-insight-table-wrap"><table class="ss-experiment-table">'
            f'<thead><tr>{header}</tr></thead><tbody>{"".join(body_rows)}</tbody>'
            '</table></div>',
            unsafe_allow_html=True,
        )
    else:
        st.caption("No snapshots saved yet. Complete at least one round, then save a snapshot.")
