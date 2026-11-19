"""Honest metrics for the fictional, synthetic SMARTSCAN demonstration."""
from __future__ import annotations
from simulation import SECTORS, TOTAL_ROUNDS, SimulationState

INITIAL_KPIS = {"pd": "0.0%", "pfa": "N/A", "avg_reward": "+0.00", "observed_yield": "0.0%"}


def _pct(num: float, den: float) -> str:
    return f"{(num / den * 100) if den > 0 else 0:.1f}%"


def compute_kpis(sim: SimulationState) -> dict:
    """Return display-ready metrics without inventing unsupported measures.

    Pd is the fraction of all synthetic active sector-round events that were
    observed. Pfa is unavailable because the simulator has no false-positive
    sensor model. Observed active yield is detections divided by observations;
    it is not prediction accuracy.
    """
    if sim.round == 0:
        return dict(INITIAL_KPIS)
    allocations = sim.total_allocations
    return {
        "pd": _pct(sim.total_detected, sim.total_ground_truth),
        "pfa": "N/A",
        "avg_reward": f"{(sim.cumulative_reward / sim.round) if sim.round else 0:+.2f}",
        "observed_yield": _pct(sim.total_detected, allocations),
    }


def progress_pct(sim: SimulationState) -> float:
    return sim.round / TOTAL_ROUNDS * 100


def allocation_share(sim: SimulationState) -> dict:
    """Fraction of recorded observations associated with each fictional sector."""
    total = sum(sim.visits.values())
    return {s.id: (sim.visits[s.id] / total if total else 0.0) for s in SECTORS}
