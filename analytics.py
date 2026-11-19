"""KPI and performance calculations (pure Python)."""
from __future__ import annotations

from simulation import SECTORS, TOTAL_ROUNDS, SimulationState

# Values the original page shows before any round has run.
INITIAL_KPIS = {"pd": "84.5%", "pfa": "14.2%", "avg_reward": "+7.51", "accuracy": "78.2%"}


def _pct(num: float, den: float) -> str:
    return f"{(num / den * 100) if den > 0 else 0:.1f}%"


def compute_kpis(sim: SimulationState) -> dict:
    """Display strings for the four hero KPIs.

    pd         = detections / all truly-active sector-rounds   (JS: kpi-comp)
    pfa        = idle scans / scans                            (JS: kpi-idle)
    avg_reward = cumulative reward / rounds played             (label says "per round")
    accuracy   = detections / scans                            (JS: kpi-eff)
    """
    if sim.round == 0:
        return dict(INITIAL_KPIS)
    avg = sim.cumulative_reward / sim.round
    return {
        "pd": _pct(sim.total_detected, sim.total_ground_truth),
        "pfa": _pct(sim.total_idle, sim.total_allocations),
        "avg_reward": f"{avg:+.2f}",
        "accuracy": _pct(sim.total_detected, sim.total_allocations),
    }


def progress_pct(sim: SimulationState) -> float:
    return sim.round / TOTAL_ROUNDS * 100


def allocation_share(sim: SimulationState) -> dict:
    """Fraction of all scans spent on each sector (drives the radar halos)."""
    total = sum(sim.visits.values())
    return {s.id: (sim.visits[s.id] / total if total else 0.0) for s in SECTORS}
