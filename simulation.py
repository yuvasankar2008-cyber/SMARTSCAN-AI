"""SMARTSCAN AI simulation engine (pure Python, no UI imports).

This is a line-by-line port of the JavaScript engine in the original portal:
sector table, UCB1 + priority utility + staleness scoring, ground-truth
generation, reward logic, history and CSV export.
"""
from __future__ import annotations

import csv
import io
import math
import random
from dataclasses import dataclass
from typing import Optional

# --- configuration (identical to the original JS constants) -----------------
TOTAL_ROUNDS = 100
DEFAULT_C = 1.4
STALENESS_GAMMA = 0.35      # the "0.35" multiplier in the original staleness term
IDLE_PENALTY = 2            # points lost on an idle scan
SURGE_START, SURGE_END = 25, 85

# Cyclic drift is selectable in the original UI but was never implemented in
# the JS. Defined here: every DRIFT_PERIOD rounds a different sector becomes the
# "hot" sector (probability DRIFT_HOT_PROB); everything else keeps its baseline.
DRIFT_PERIOD = 20
DRIFT_HOT_PROB = 0.85


@dataclass(frozen=True)
class Sector:
    id: str
    name: str
    angle: int
    prio: float
    prob: float
    color: str
    burst_prob: Optional[float] = None

    @property
    def reward(self) -> int:
        return int(round(self.prio * 10))


SECTORS = (
    Sector("SEC_ALPHA", "Alpha", 45, 3.0, 0.65, "#3b82f6"),
    Sector("SEC_BRAVO", "Bravo", 120, 2.0, 0.40, "#8b5cf6"),
    Sector("SEC_CHARLIE", "Charlie", 195, 1.0, 0.15, "#06b6d4"),
    Sector("SEC_DELTA", "Delta", 270, 4.0, 0.15, "#f59e0b", burst_prob=0.85),
    Sector("SEC_ECHO", "Echo", 330, 1.5, 0.45, "#10b981"),
)

SCENARIOS = {
    "dynamic_surge": "Dynamic Surge (Delta Spikes)",
    "cyclic_drift": "Cyclic Drift (Shifting Load)",
    "stationary": "Stationary Baseline",
}
BEAM_OPTIONS = {1: "1 Observation Beam", 2: "2 Concurrent Beams"}

INIT_MESSAGE = "[INIT] SMARTSCAN AI Autonomous Engine initialized. Awaiting run command."
RESET_MESSAGE = "[RESET] Simulation reset to initial state."


def activity_probability(sector: Sector, scenario: str, rnd: int) -> float:
    """Probability that `sector` is truly active in round `rnd`."""
    if (scenario == "dynamic_surge" and sector.id == "SEC_DELTA"
            and SURGE_START <= rnd <= SURGE_END):
        return sector.burst_prob
    if scenario == "cyclic_drift":
        hot = SECTORS[((rnd - 1) // DRIFT_PERIOD) % len(SECTORS)]
        if sector.id == hot.id:
            return DRIFT_HOT_PROB
    return sector.prob


class SimulationState:
    """All mutable simulation state. Lives in st.session_state."""

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self.reset(announce=False)

    # -- lifecycle -------------------------------------------------------
    def reset(self, announce: bool = True) -> None:
        self.round = 0
        self.visits = {s.id: 0 for s in SECTORS}
        self.detects = {s.id: 0 for s in SECTORS}
        self.last_visited = {s.id: 0 for s in SECTORS}
        self.cumulative_reward = 0
        self.total_detected = 0
        self.total_ground_truth = 0
        self.total_false_alarms = 0
        self.total_inactive_observations = 0
        self.total_predictions = 0
        self.total_correct_predictions = 0
        self.total_allocations = 0
        self.total_idle = 0
        self.history: list[dict] = []
        self.ground_truth_history: list[dict] = []
        self.active_events: list[dict] = []
        self.current_active_event_ids: dict[str, Optional[int]] = {
            s.id: None for s in SECTORS
        }
        self.last_events: list[dict] = []
        self.log: list[dict] = [{"kind": "system",
                                 "text": RESET_MESSAGE if announce else INIT_MESSAGE}]

    @property
    def finished(self) -> bool:
        return self.round >= TOTAL_ROUNDS

    # -- decision logic --------------------------------------------------
    def _estimated_activity(self, sector: Sector) -> float:
        """Laplace-smoothed active rate from this sector's prior observations."""
        return (self.detects[sector.id] + 1) / (self.visits[sector.id] + 2)

    def score(self, s: Sector, c: float) -> tuple[float, float, float, float]:
        """(total, utility, ucb_bonus, staleness) - same maths as the JS."""
        n = self.visits[s.id]
        p_hat = self._estimated_activity(s)
        utility = p_hat * s.prio * 10
        ucb = c * math.sqrt((2 * math.log(self.round + 1)) / (n + 1))
        staleness = (self.round - self.last_visited[s.id]) * (s.prio / 2) * STALENESS_GAMMA
        return utility + ucb + staleness, utility, ucb, staleness

    def select_sectors(self, c: float = DEFAULT_C, beams: int = 1) -> list[tuple[Sector, str]]:
        """Pick `beams` distinct sectors. Cold start first, then highest score."""
        picks: list[tuple[Sector, str]] = []
        for s in [s for s in SECTORS if self.visits[s.id] == 0][:beams]:
            picks.append((s, f"[COLD-START] Exploring {s.name} to establish baseline."))
        if len(picks) >= beams:
            return picks

        taken = {s.id for s, _ in picks}
        scored = [(self.score(s, c), s) for s in SECTORS if s.id not in taken]
        scored.sort(key=lambda x: -x[0][0])          # stable: ties keep sector order
        for (_, utility, ucb, stale), s in scored[: beams - len(picks)]:
            picks.append((s, f"[EXPLOIT] {s.name}: Utility={utility:.1f}, "
                             f"UCB=+{ucb:.1f}, Staleness=+{stale:.1f}"))
        return picks

    # -- one round -------------------------------------------------------
    def step(self, scenario: str = "dynamic_surge", c: float = DEFAULT_C,
             beams: int = 1) -> list[dict]:
        if self.finished:
            return []
        self.round += 1

        truth: dict[str, bool] = {}
        for s in SECTORS:
            active = self.rng.random() < activity_probability(s, scenario, self.round)
            truth[s.id] = active
            if active:
                self.total_ground_truth += 1
                event_id = self.current_active_event_ids[s.id]
                if event_id is None:
                    event_id = len(self.active_events) + 1
                    self.active_events.append({
                        "id": event_id,
                        "sector_id": s.id,
                        "sector": s.name,
                        "start_round": self.round,
                        "end_round": self.round,
                        "first_observed_round": None,
                    })
                    self.current_active_event_ids[s.id] = event_id
                event = self.active_events[event_id - 1]
                event["end_round"] = self.round
                start_round = event["start_round"]
            else:
                self.current_active_event_ids[s.id] = None
                event_id = None
                start_round = None
            self.ground_truth_history.append({
                "round": self.round,
                "sector_id": s.id,
                "active": active,
                "active_event_id": event_id,
                "activity_start_round": start_round,
            })

        picks = self.select_sectors(c, beams)       # all beams decide on pre-round stats
        events = []
        for sector, reason in picks:
            self.total_allocations += 1
            predicted_active = self._estimated_activity(sector) > 0.5
            self.visits[sector.id] += 1
            self.last_visited[sector.id] = self.round
            detected = truth[sector.id]
            self.total_predictions += 1
            prediction_correct = predicted_active == detected
            if prediction_correct:
                self.total_correct_predictions += 1
            if not detected:
                self.total_inactive_observations += 1
                if predicted_active:
                    self.total_false_alarms += 1
            if detected:
                self.detects[sector.id] += 1
                self.total_detected += 1
                event_id = self.current_active_event_ids[sector.id]
                event = self.active_events[event_id - 1]
                if event["first_observed_round"] is None:
                    event["first_observed_round"] = self.round
                delta = sector.reward
            else:
                event_id = None
                self.total_idle += 1
                delta = -IDLE_PENALTY
            self.cumulative_reward += delta
            activity_start_round = (
                self.active_events[event_id - 1]["start_round"]
                if event_id is not None else None
            )
            first_observed_round = (
                self.active_events[event_id - 1]["first_observed_round"]
                if event_id is not None else None
            )
            self.history.append({"round": self.round, "selected": sector.name,
                                 "detected": detected, "reward": self.cumulative_reward,
                                 "predicted_active": predicted_active,
                                 "prediction_correct": prediction_correct,
                                 "false_alarm": not detected and predicted_active,
                                 "active_event_id": event_id,
                                 "activity_start_round": activity_start_round,
                                 "first_observed_round": first_observed_round})
            event = {"kind": "decision", "round": self.round, "sector_id": sector.id,
                     "sector": sector.name, "detected": detected,
                     "predicted_active": predicted_active, "reward": delta,
                     "reason": reason}
            events.append(event)
            self.log.append(event)

        self.last_events = events
        if self.finished:
            self.log.append({"kind": "system",
                             "text": f"[COMPLETE] {TOTAL_ROUNDS} rounds finished. "
                                     "Export the CSV or press Reset to run again."})
        return events


def history_to_csv(history: list[dict], metrics: Optional[dict[str, str]] = None) -> str:
    """Export observed outcomes and the run-level metric snapshot."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    metric_fields = [
        ("Run_Pfa", "pfa"),
        ("Run_Mean_Intercept_Rate", "mean_intercept_rate"),
        ("Run_Average_Intercept_Time_Error", "avg_intercept_time_error"),
        ("Run_Correct_Prediction_Percentage", "correct_prediction_pct"),
    ]
    w.writerow([
        "Round", "Selected_Sector", "Detected", "Predicted_Active",
        "Prediction_Correct", "False_Alarm", "Activity_Start_Round",
        "First_Observed_Round", "Cumulative_Reward",
        *(label for label, _ in metric_fields),
    ])
    for h in history:
        w.writerow([
            h["round"], h["selected"], str(h["detected"]).lower(),
            str(h["predicted_active"]).lower(),
            str(h["prediction_correct"]).lower(), str(h["false_alarm"]).lower(),
            h["activity_start_round"], h["first_observed_round"], h["reward"],
            *(metrics.get(key, "N/A") if metrics else "N/A" for _, key in metric_fields),
        ])
    return buf.getvalue()
