"""SMARTSCAN AI - Streamlit entry point.   Run:  streamlit run app.py"""
from pathlib import Path

import streamlit as st

from analytics import compute_kpis
from components.dashboard import render_analytics, render_hero
from components.layout import footer_html, header_html
from components.mission_control import (advance, render_mission_control,
                                        render_radar_card)
from components.pitch_deck import render_pitch_deck
from simulation import TOTAL_ROUNDS, SimulationState

TICK_SECONDS = 0.1   # live-run speed (the original JS used 70 ms)

st.set_page_config(page_title="SMARTSCAN AI | Intelligent Adaptive Scan Scheduling - SIH 2026",
                   page_icon="📡", layout="wide", initial_sidebar_state="collapsed")

css = (Path(__file__).parent / "styles.css").read_text(encoding="utf-8")
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

ss = st.session_state
if "sim" not in ss:
    ss.sim = SimulationState()
    ss.running = False
    ss.slide = 0


def live_section() -> None:
    """Hero KPIs + radar + mission control. Re-runs on a timer while running."""

    @st.fragment(run_every=TICK_SECONDS if ss.running else None)
    def live():
        if ss.pop("_rerun_app", False):
            st.rerun()                      # Run/Pause/Reset: re-evaluate the timer
        if ss.running:
            advance()
            if ss.sim.round >= TOTAL_ROUNDS:
                ss.running = False
                st.rerun()                  # finished: switch the timer off
        render_hero(compute_kpis(ss.sim))
        with st.container(key="sim_row"):
            left, right = st.columns([5, 7])
            with left:
                render_radar_card(ss.sim)
            with right:
                render_mission_control(ss.sim)

    live()


st.markdown(header_html(), unsafe_allow_html=True)
live_section()
render_analytics()
render_pitch_deck()
st.markdown(footer_html(), unsafe_allow_html=True)
