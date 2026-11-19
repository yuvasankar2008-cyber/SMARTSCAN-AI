"""Radar card + Simulation Mission Control (controls, progress, telemetry, CSV)."""
from analytics import compute_kpis, progress_pct
from components import clean, esc
from radar import radar_svg
from simulation import (BEAM_OPTIONS, DEFAULT_C, SCENARIOS, TOTAL_ROUNDS,
                        SimulationState, history_to_csv)
#from graph import render_simulation_progress
LOG_LINES_SHOWN = 50   # newest first; keeps each live re-render small


# ---------------------------------------------------------------- builders
def radar_card_html(sim: SimulationState) -> str:
    return clean(f"""
<div class="ss-anchor" id="simulation-suite">
<div class="ss-radar-head">
<div class="ss-radar-title"><span class="ss-dot-lg live-pulse"></span><span>Synthetic Sector Activity Map</span></div>
<span class="ss-xs-muted" id="radar-mode">5 fictional sectors</span>
</div>
</div>
<div class="ss-radar-wrap">
<div class="ss-radar">{radar_svg(sim)}</div>
<div class="ss-radar-center"><div class="ss-radar-dot"></div></div>
</div>
<div class="ss-legend">
<div class="ss-leg ss-leg-blue">ALPHA (3x)</div>
<div class="ss-leg ss-leg-purple">BRAVO (2x)</div>
<div class="ss-leg ss-leg-cyan">CHARLIE (1x)</div>
<div class="ss-leg ss-leg-amber">DELTA (4x)</div>
<div class="ss-leg ss-leg-emerald">ECHO (1.5x)</div>
</div>
""")


def mission_head_html(sim: SimulationState) -> str:
    return clean(f"""
<div class="ss-mc-head">
<div>
<div class="ss-h3" role="heading" aria-level="3">Simulation Mission Control</div>
<div class="ss-xs-muted">Advance a fictional synthetic environment and review recorded observations</div>
</div>
<span class="ss-round-chip" id="sim-round-display">Round: {sim.round} / {TOTAL_ROUNDS}</span>
</div>
""")


def progress_html(sim: SimulationState) -> str:
    return (f'<div class="ss-progress"><div class="ss-progress-bar" id="sim-progress" '
            f'style="width:{progress_pct(sim):.0f}%"></div></div>')


def telemetry_html(sim: SimulationState) -> str:
    lines = []
    for e in reversed(sim.log[-LOG_LINES_SHOWN:]):
        if e["kind"] == "system":
            lines.append(f'<div class="c-cyan">{esc(e["text"])}</div>')
        elif e["detected"]:
            lines.append(f'<div><span class="c-cyan">R{e["round"]}</span> → <b>{esc(e["sector"])}</b>: '
                         f'<span class="c-emerald fw-b">DETECTED ACTIVE</span> (+{e["reward"]} pts) | '
                         f'<span class="c-slate">Synthetic observation recorded</span></div>')
        else:
            lines.append(f'<div><span class="c-cyan">R{e["round"]}</span> → <b>{esc(e["sector"])}</b>: '
                         f'<span class="c-slate">IDLE SCAN</span> ({e["reward"]} pts) | '
                         f'<span class="c-slate">Synthetic observation recorded</span></div>')
    return clean(f"""
<div class="ss-telemetry-label">Live Synthetic Event Log</div>
<div class="ss-telemetry" id="telemetry-log">{"".join(lines)}</div>
""")


# ---------------------------------------------------------------- callbacks
def _ss():
    import streamlit as st
    return st.session_state


def start_cb():
    ss = _ss()
    if not ss.sim.finished:
        ss.running = True
        ss._rerun_app = True      # full rerun so the fragment timer switches on


def pause_cb():
    ss = _ss()
    ss.running = False
    ss._rerun_app = True


def step_cb():
    advance()


def reset_cb():
    ss = _ss()
    ss.sim.reset()
    ss.running = False
    ss._rerun_app = True


def advance() -> None:
    """Run one round using the current control values (same as JS stepSim)."""
    ss = _ss()
    ss.sim.step(scenario=ss.get("scenario", "dynamic_surge"),
                c=float(ss.get("c_param", DEFAULT_C)),
                beams=int(ss.get("beams", 1)))


# ---------------------------------------------------------------- render
def render_radar_card(sim: SimulationState) -> None:
    import streamlit as st
    with st.container(key="radar_card"):
        st.markdown(radar_card_html(sim), unsafe_allow_html=True)


def render_mission_control(sim: SimulationState) -> None:
    import streamlit as st
    with st.container(key="mission_card"):
        st.markdown(mission_head_html(sim), unsafe_allow_html=True)

        with st.container(key="ctrl_row"):
            c1, c2, c3 = st.columns(3)
            c1.selectbox("Scenario Mode", list(SCENARIOS), key="scenario",
                         format_func=SCENARIOS.get)
            c2.selectbox("Observation Beams", list(BEAM_OPTIONS), key="beams",
                         format_func=BEAM_OPTIONS.get)
            c3.slider("UCB Exploration (c)", 0.5, 2.5, DEFAULT_C, 0.1, key="c_param")

        st.markdown(progress_html(sim), unsafe_allow_html=True)

        with st.container(key="btn_bar"):
            b1, b2, b3, b4, b5 = st.columns([1.7, 1, 1.15, 1, 1.35])
            b1.button("▶ Run Live Simulation", key="btn_start", on_click=start_cb)
            b2.button("⏸ Pause", key="btn_pause", on_click=pause_cb)
            b3.button("⏭ Step Round", key="btn_step", on_click=step_cb)
            b4.button(" Reset", key="btn_reset", on_click=reset_cb)
            b5.download_button("Export CSV", data=history_to_csv(
                                   sim.history, compute_kpis(sim)),      # Simulation Progress Graph
                               file_name="smartscan_simulation_results.csv",
                               mime="text/csv", key="btn_csv",
                               disabled=not sim.history,
                               help=None if sim.history else
                               "Run at least one round to generate CSV data.")
        # SIMULATION PROGRESS GRAPH
        #render_simulation_progress(sim)

        st.markdown(telemetry_html(sim), unsafe_allow_html=True)
