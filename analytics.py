"""Honest metrics for the fictional, synthetic SMARTSCAN demonstration."""
from __future__ import annotations
from simulation import SECTORS, TOTAL_ROUNDS, SimulationState

INITIAL_KPIS = {
    "pd": "N/A",
    "pfa": "N/A",
    "avg_reward": "+0.00",
    "observed_yield": "N/A",
    "mean_intercept_rate": "N/A",
    "avg_intercept_time_error": "N/A",
    "correct_prediction_pct": "N/A",
}


def _pct(num: float, den: float) -> str:
    return f"{num / den * 100:.1f}%" if den > 0 else "N/A"


def compute_kpis(sim: SimulationState) -> dict:
    """Return display-ready metrics computed from synthetic outcomes."""
    if sim.round == 0:
        return dict(INITIAL_KPIS)
    allocations = sim.total_allocations
    intercepted_events = [
        event for event in sim.active_events
        if event["first_observed_round"] is not None
    ]
    time_error = (
        sum(
            abs(event["first_observed_round"] - event["start_round"])
            for event in intercepted_events
        ) / len(intercepted_events)
        if intercepted_events else None
    )
    return {
        "pd": _pct(sim.total_detected, sim.total_ground_truth),
        "pfa": _pct(sim.total_false_alarms, sim.total_inactive_observations),
        "avg_reward": f"{(sim.cumulative_reward / sim.round) if sim.round else 0:+.2f}",
        "observed_yield": _pct(sim.total_detected, allocations),
        "mean_intercept_rate": _pct(len(intercepted_events), len(sim.active_events)),
        "avg_intercept_time_error": (
            f"{time_error:.1f} rounds" if time_error is not None else "N/A"
        ),
        "correct_prediction_pct": _pct(
            sim.total_correct_predictions, sim.total_predictions
        ),
    }


def progress_pct(sim: SimulationState) -> float:
    return sim.round / TOTAL_ROUNDS * 100


def allocation_share(sim: SimulationState) -> dict:
    """Fraction of recorded observations associated with each fictional sector."""
    total = sum(sim.visits.values())
    return {s.id: (sim.visits[s.id] / total if total else 0.0) for s in SECTORS}
