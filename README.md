# SMARTSCAN AI — Python / Streamlit edition

The original SMARTSCAN AI portal (SIH 2026, Team AetherX) with all JavaScript logic
moved to Python. Markup and styling follow the original page; there is no JavaScript
anywhere in the project.

## Run

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt                      # streamlit>=1.40
streamlit run app.py                                 # opens http://localhost:8501
```

Headless checks (no Streamlit needed): `pip install pytest && python -m pytest -q`

## Layout

| File | Role |
|---|---|
| `app.py` | Streamlit entry point, session state, live-run timer |
| `simulation.py` | Sectors, UCB1 + utility + staleness scoring, scenarios, rewards, history, CSV |
| `analytics.py` | Clearly defined synthetic Pd, unavailable Pfa, average reward and observed active yield |
| `radar.py` | Radar drawn as inline SVG from Python (rings, crosshairs, blips, sweep) |
| `components/` | Existing layout, dashboard, mission control and pitch deck, plus `insights.py` (heatmap, scenario profiles, event summary, experiment history and guided demo) |
| `styles.css` | The original look: dark cyber theme, glass cards, neon text, glow |
| `.streamlit/config.toml` | Dark theme colours for native widgets |

## JavaScript → Python map

| Original JS | Python |
|---|---|
| `SECTORS`, state variables | `simulation.SECTORS`, `SimulationState` |
| `selectSectorAdaptive()` | `SimulationState.select_sectors()` / `.score()` |
| `stepSim()` | `SimulationState.step()` |
| `startSim` / `pauseSim` / `resetSim` | `start_cb` / `pause_cb` / `reset_cb` + `st.fragment(run_every=…)` timer in `app.py` |
| KPI `innerText` updates | `analytics.compute_kpis()` → `dashboard.hero_html()` |
| `drawRadar()` canvas loop | `radar.radar_svg()` (+ CSS rotation for the sweep) |
| `downloadCSV()` | `simulation.history_to_csv()` + `st.download_button` |
| `SLIDES`, `renderSlide`, `next/prevSlide` | `pitch_deck.SLIDES`, `st.session_state.slide`, Prev/Next buttons |
| `scrollToSim()` | plain `#simulation-suite` anchor link |

## Differences from the original (and why)

1. **Tailwind → hand-written CSS.** The page loaded the Tailwind Play CDN, which is a
   JavaScript runtime. Its utilities are re-expressed in `styles.css` with the same colours,
   sizes and effects, so the look should match closely but is not byte-identical.
2. **Native widgets.** Dropdowns, slider and buttons are Streamlit widgets themed to match;
   their exact shape and spacing differ slightly from the HTML controls.
3. **Live run speed.** The timer ticks every 0.1 s (`TICK_SECONDS` in `app.py`); the JS used 70 ms.
   Each tick re-renders the fragment, so open dropdowns may close while a run is in progress —
   press Pause first to change settings.
4. **Radar animation.** The sweep is a CSS rotation (phase synced to the clock so re-renders
   don't restart it). Blips update once per simulation tick, not at 60 fps. Added: halo size =
   share of scans, ring on the last scanned sector (green = detected), visit counts.
5. **Observation Beams and Cyclic Drift were never implemented in the JS** (the controls existed
   but were ignored). Defined here: 2 beams = the two top-scoring distinct sectors per round
   (each scan counts as an allocation); Cyclic Drift = a different sector becomes hot
   (p = 0.85) every 20 rounds.
6. **Formula.** The brief's formula omits the `0.35` staleness factor and uses `ln(t)/N`; the JS
   actually computes `ln(round+1)/(N+1)` and staleness × `(W/2)` × `0.35`. The JS behaviour was kept.
7. **Average Reward** is now cumulative reward ÷ rounds played (the JS showed the cumulative
   total under an "Average / Points per Round" label). The CSV still exports cumulative reward.
8. **Metric reporting.** Initial values are neutral. Pd uses the synthetic active-event ground truth; Pfa is marked N/A because no false-positive sensor model exists; observed active yield is not prediction accuracy.
9. Telemetry shows the latest 50 lines (the full history is still exported); "bravo" is now "Bravo".
10. The "Streamlit Dashboard" header link still points to `localhost:8501` as in the original.
11. Export CSV is disabled until at least one round exists (replaces the JS `alert`).

## Reporting note

The updated hero and pitch deck remove unsupported performance comparisons and real-world deployment claims. The scenario comparison shows expected synthetic activity profiles only; it is not a scheduler benchmark.


## Added prototype features

- Compact simulation completion panel that refreshes with the live simulation.
- Recorded-observation heatmap: blank cells explicitly mean not observed.
- Scenario profile comparison against the stationary synthetic reference (not a scheduler benchmark).
- Descriptive latest-event panel and session-only experiment snapshots.
- Guided presenter walkthrough.
- KPI definitions corrected: false-alarm probability is N/A without a false-positive model; observed active yield is not prediction accuracy.

## Scope and interpretation

This is a fictional, non-operational educational simulation. It is not connected to RF hardware, real emitters, or operational systems. Scenario profile comparisons describe generated synthetic activity patterns and do not establish real-world detection or interception performance. Experiment history is held in Streamlit session state and is not permanent storage.
