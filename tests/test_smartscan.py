"""Headless checks (no Streamlit needed):  python -m pytest -q   or   python tests/test_smartscan.py"""
import csv
import io
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from analytics import INITIAL_KPIS, compute_kpis  # noqa: E402
from components.dashboard import analytics_html, hero_html  # noqa: E402
from components.mission_control import (progress_html, radar_card_html,  # noqa: E402
                                        telemetry_html)
from components.pitch_deck import SLIDES, slide_html  # noqa: E402
from radar import radar_svg  # noqa: E402
from simulation import (DRIFT_PERIOD, SCENARIOS, SECTORS, TOTAL_ROUNDS,  # noqa: E402
                        SimulationState, activity_probability, history_to_csv)


def run_full(scenario, beams=1, seed=7, c=1.4):
    sim = SimulationState(seed=seed)
    for _ in range(TOTAL_ROUNDS + 5):          # extra calls must be no-ops
        sim.step(scenario, c, beams)
    return sim


def test_all_scenarios_run_and_cap_at_100():
    for sc in SCENARIOS:
        for beams in (1, 2):
            sim = run_full(sc, beams)
            assert sim.round == TOTAL_ROUNDS and sim.finished
            assert sim.total_allocations == TOTAL_ROUNDS * beams
            assert len(sim.history) == TOTAL_ROUNDS * beams


def test_statistics_are_consistent():
    for sc in SCENARIOS:
        sim = run_full(sc)
        assert sum(sim.visits.values()) == sim.total_allocations
        assert sum(sim.detects.values()) == sim.total_detected
        assert sim.total_detected + sim.total_idle == sim.total_allocations
        assert len(sim.ground_truth_history) == TOTAL_ROUNDS * len(SECTORS)
        assert sim.total_predictions == sim.total_allocations
        assert sim.total_correct_predictions == sum(h["prediction_correct"] for h in sim.history)
        assert sim.total_false_alarms == sum(h["false_alarm"] for h in sim.history)
        assert sim.total_inactive_observations == sum(not h["detected"] for h in sim.history)
        assert sim.total_ground_truth == sum(row["active"] for row in sim.ground_truth_history)
        prior_visits = {s.id: 0 for s in SECTORS}
        prior_detects = {s.id: 0 for s in SECTORS}
        by_name = {s.name: s for s in SECTORS}
        for row in sim.history:
            sector = by_name[row["selected"]]
            expected_prediction = (
                (prior_detects[sector.id] + 1) / (prior_visits[sector.id] + 2) > 0.5
            )
            assert row["predicted_active"] == expected_prediction
            prior_visits[sector.id] += 1
            prior_detects[sector.id] += row["detected"]
        by_id = {s.name: s for s in SECTORS}
        expect = sum(by_id[h["selected"]].reward if h["detected"] else -2 for h in sim.history)
        assert expect == sim.cumulative_reward == sim.history[-1]["reward"]
        assert sim.total_detected <= sim.total_ground_truth
        assert all(
            event["first_observed_round"] is None
            or event["start_round"] <= event["first_observed_round"] <= event["end_round"]
            for event in sim.active_events
        )


def test_cold_start_visits_every_sector_first():
    sim = SimulationState(seed=1)
    first = [sim.step()[0]["sector"] for _ in range(5)]
    assert first == [s.name for s in SECTORS]
    assert sim.step()[0]["reason"].startswith("[EXPLOIT]")


def test_two_beams_pick_distinct_sectors():
    sim = SimulationState(seed=3)
    for _ in range(40):
        ev = sim.step("stationary", 1.4, 2)
        assert len({e["sector_id"] for e in ev}) == 2


def test_score_matches_original_formula():
    import math
    sim = SimulationState(seed=2)
    for _ in range(12):
        sim.step()
    s = SECTORS[0]
    n, d = sim.visits[s.id], sim.detects[s.id]
    exp = ((d + 1) / (n + 2) * s.prio * 10
           + 1.4 * math.sqrt(2 * math.log(sim.round + 1) / (n + 1))
           + (sim.round - sim.last_visited[s.id]) * s.prio / 2 * 0.35)
    assert abs(sim.score(s, 1.4)[0] - exp) < 1e-9


def test_scenarios_change_ground_truth_probabilities():
    delta = next(s for s in SECTORS if s.id == "SEC_DELTA")
    assert activity_probability(delta, "dynamic_surge", 24) == 0.15
    assert activity_probability(delta, "dynamic_surge", 25) == 0.85
    assert activity_probability(delta, "dynamic_surge", 85) == 0.85
    assert activity_probability(delta, "dynamic_surge", 86) == 0.15
    assert activity_probability(delta, "stationary", 50) == 0.15
    hot = {r: [s.name for s in SECTORS if activity_probability(s, "cyclic_drift", r) == 0.85]
           for r in (1, DRIFT_PERIOD, DRIFT_PERIOD + 1, 100)}
    assert hot[1] == hot[DRIFT_PERIOD] == ["Alpha"] and hot[DRIFT_PERIOD + 1] == ["Bravo"]
    assert hot[100] == ["Echo"]


def test_surge_is_exploited_on_average():
    shares = []
    for seed in range(20):
        sim = run_full("dynamic_surge", seed=seed)
        shares.append(sim.visits["SEC_DELTA"])
    assert sum(shares) / len(shares) > 25      # well above a 20-visit round-robin share


def test_reset_clears_everything():
    sim = run_full("dynamic_surge")
    sim.reset()
    assert sim.round == 0 and sim.history == [] and sim.cumulative_reward == 0
    assert sim.ground_truth_history == [] and sim.active_events == []
    assert all(v == 0 for v in {**sim.visits, **sim.detects, **sim.last_visited}.values())
    assert (sim.total_allocations == sim.total_idle == sim.total_detected
            == sim.total_ground_truth == sim.total_false_alarms
            == sim.total_inactive_observations == sim.total_predictions
            == sim.total_correct_predictions == 0)
    assert compute_kpis(sim) == INITIAL_KPIS
    assert sim.log[0]["text"].startswith("[RESET]")


def test_kpis():
    assert compute_kpis(SimulationState()) == INITIAL_KPIS
    sim = run_full("stationary")
    k = compute_kpis(sim)
    assert k["observed_yield"] == f"{sim.total_detected / sim.total_allocations * 100:.1f}%"
    assert k["pfa"] == f"{sim.total_false_alarms / sim.total_inactive_observations * 100:.1f}%"
    assert sim.total_false_alarms > 0
    assert k["pd"] == f"{sim.total_detected / sim.total_ground_truth * 100:.1f}%"
    assert k["avg_reward"] == f"{sim.cumulative_reward / sim.round:+.2f}"
    intercepted = [e for e in sim.active_events if e["first_observed_round"] is not None]
    assert k["mean_intercept_rate"] == f"{len(intercepted) / len(sim.active_events) * 100:.1f}%"
    avg_error = sum(
        abs(e["first_observed_round"] - e["start_round"]) for e in intercepted
    ) / len(intercepted)
    assert k["avg_intercept_time_error"] == f"{avg_error:.1f} rounds"
    assert k["correct_prediction_pct"] == (
        f"{sim.total_correct_predictions / sim.total_predictions * 100:.1f}%"
    )
    assert sum(not row["detected"] for row in sim.history) == sim.total_inactive_observations


def test_csv_export():
    sim = run_full("dynamic_surge", beams=2)
    kpis = compute_kpis(sim)
    rows = list(csv.reader(io.StringIO(history_to_csv(sim.history, kpis))))
    assert rows[0] == [
        "Round", "Selected_Sector", "Detected", "Predicted_Active",
        "Prediction_Correct", "False_Alarm", "Activity_Start_Round",
        "First_Observed_Round", "Cumulative_Reward", "Run_Pfa",
        "Run_Mean_Intercept_Rate", "Run_Average_Intercept_Time_Error",
        "Run_Correct_Prediction_Percentage",
    ]
    assert len(rows) == 1 + len(sim.history)
    assert rows[1][2] in ("true", "false")
    assert rows[1][9:] == [
        kpis["pfa"], kpis["mean_intercept_rate"],
        kpis["avg_intercept_time_error"], kpis["correct_prediction_pct"],
    ]


def test_pitch_deck_has_five_slides_and_wraps():
    assert len(SLIDES) == 5
    for i in range(5):
        assert SLIDES[i]["title"].split()[0] in slide_html(i)
    assert slide_html(5) == slide_html(0)


def test_html_builders_have_no_javascript_and_no_blank_lines():
    sim = run_full("dynamic_surge", beams=2)
    blobs = [hero_html(compute_kpis(sim)), analytics_html(compute_kpis(sim)), radar_card_html(sim),
             telemetry_html(sim), progress_html(sim), slide_html(2), radar_svg(sim)]
    for b in blobs:
        assert not re.search(r"<script|onclick|javascript:", b, re.I)
        assert "\n\n" not in b                 # keeps Streamlit markdown in one HTML block
        assert not re.search(r"^\s{4,}", b, re.M)
    css = (ROOT / "styles.css").read_text()
    assert "<script" not in css


def test_no_javascript_in_project():
    for p in ROOT.rglob("*"):
        if (p.suffix in {".js", ".ts", ".jsx", ".tsx"}
                and not any(part in {".venv", "venv", "node_modules"} for part in p.parts)):
            raise AssertionError(f"JS/TS file found: {p}")
    app_code = "".join(
        p.read_text() for p in ROOT.rglob("*.py")
        if "tests" not in p.parts
        and not any(part in {".venv", "venv", "node_modules"} for part in p.parts)
    )
    assert not re.search(r"<script|onclick=|setInterval|requestAnimationFrame", app_code)


def test_radar_reflects_state():
    sim = SimulationState(seed=5)
    idle = radar_svg(sim, now=0)
    for _ in range(10):
        sim.step()
    busy = radar_svg(sim, now=0)
    assert busy != idle and "stroke-width=\"2\"" in busy and "ss-sweep" in busy
    for name in ("Alpha", "Bravo", "Charlie", "Delta", "Echo"):
        assert name in busy


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", name)
            except Exception as exc:  # noqa: BLE001
                fails += 1
                print("FAIL", name, repr(exc))
    sys.exit(1 if fails else 0)
