"""Python-rendered surveillance radar (inline SVG).

Same geometry as the original canvas: 320x320, rings at 40/80/120/150, crosshairs,
five independently moving radar targets, gradient sweep cone + sweep line. The
sweep is a pure-CSS rotation (see styles.css); its phase is taken from the wall
clock here so it stays continuous when Streamlit re-renders the SVG. Targets move
smoothly between deterministic random waypoints, while their halos and detection
rings continue to reflect the simulation.
"""
from __future__ import annotations

import math
import random
import time
from typing import Optional

from analytics import allocation_share
from simulation import SECTORS, SimulationState

SIZE = 320
CX = CY = SIZE / 2
R_OUT = 150
SWEEP_PERIOD = 2 * math.pi / 0.035 / 60      # original: +0.035 rad per 60fps frame
CONE = 0.4

# Targets choose a new random destination at this interval.
TARGET_MOVE_INTERVAL = 5.0

# Keep target centers comfortably inside the radar's outer ring.
TARGET_MAX_RADIUS = R_OUT - 20


def _moving_position(sector_id: str, now: float) -> tuple[float, float]:
    """Return a smooth, repeatable random position for one radar target.

    Each sector has its own random path. Using time-based waypoints makes the
    movement independent of Streamlit reruns, so a rerun does not reset a target.
    """
    interval = TARGET_MOVE_INTERVAL
    waypoint_index = int(now // interval)
    progress = (now % interval) / interval

    # Smoothstep interpolation: ease in and ease out between waypoints.
    progress = progress * progress * (3.0 - 2.0 * progress)

    def waypoint(index: int) -> tuple[float, float]:
        rng = random.Random(f"{sector_id}:{index}")
        angle = rng.uniform(0.0, 2.0 * math.pi)
        # sqrt gives a more even spread across the radar area.
        radius = TARGET_MAX_RADIUS * math.sqrt(rng.random())
        return (
            CX + radius * math.cos(angle),
            CY + radius * math.sin(angle),
        )

    start_x, start_y = waypoint(waypoint_index)
    end_x, end_y = waypoint(waypoint_index + 1)

    x = start_x + (end_x - start_x) * progress
    y = start_y + (end_y - start_y) * progress
    return x, y


def radar_svg(sim: SimulationState, now: Optional[float] = None) -> str:
    now = time.time() if now is None else now
    delay = -(now % SWEEP_PERIOD)
    share = allocation_share(sim)
    last = {e["sector_id"]: e for e in sim.last_events}

    x1 = CX + R_OUT * math.cos(-CONE)
    y1 = CY + R_OUT * math.sin(-CONE)
    out = [
        f'<svg width="{SIZE}" height="{SIZE}" viewBox="0 0 {SIZE} {SIZE}" '
        'xmlns="http://www.w3.org/2000/svg">',
        f'<defs><radialGradient id="ssSweepGrad" gradientUnits="userSpaceOnUse" '
        f'cx="{CX}" cy="{CY}" r="{R_OUT}">'
        '<stop offset="0.067" stop-color="rgb(0,242,254)" stop-opacity="0.4"/>'
        '<stop offset="1" stop-color="rgb(0,242,254)" stop-opacity="0"/>'
        '</radialGradient></defs>',
    ]
    for r in (40, 80, 120, 150):
        out.append(f'<circle cx="{CX}" cy="{CY}" r="{r}" fill="none" '
                   'stroke="rgba(0,242,254,0.15)" stroke-width="1"/>')
    out.append(f'<path d="M{CX - R_OUT} {CY}H{CX + R_OUT}M{CX} {CY - R_OUT}V{CY + R_OUT}" '
               'stroke="rgba(59,130,246,0.2)" stroke-width="1" fill="none"/>')

    for s in SECTORS:
        # Each sector (ALPHA, BRAVO, CHARLIE, DELTA, ECHO) moves independently.
        x, y = _moving_position(str(s.id), now)
        halo = 6 + share[s.id] * 16
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{halo:.1f}" fill="{s.color}" opacity="0.18"/>')
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="{s.color}"/>')
        ev = last.get(s.id)
        if ev:
            ring = "#34d399" if ev["detected"] else "#64748b"
            out.append(f'<circle class="live-pulse" cx="{x:.1f}" cy="{y:.1f}" r="13" '
                       f'fill="none" stroke="{ring}" stroke-width="2"/>')
        out.append(f'<text x="{x:.1f}" y="{y - 10:.1f}" text-anchor="middle" fill="#94a3b8" '
                   f'font-size="9" font-weight="700" font-family="system-ui">{s.name}</text>')
        out.append(f'<text x="{x:.1f}" y="{y + 21:.1f}" text-anchor="middle" fill="#64748b" '
                   f'font-size="8" font-family="system-ui">{sim.visits[s.id]}</text>')

    out.append(f'<g class="ss-sweep" style="animation-delay:{delay:.3f}s">'
               f'<path d="M{CX} {CY}L{x1:.1f} {y1:.1f}A{R_OUT} {R_OUT} 0 0 1 {CX + R_OUT} {CY}Z" '
               'fill="url(#ssSweepGrad)"/>'
               f'<line x1="{CX}" y1="{CY}" x2="{CX + R_OUT}" y2="{CY}" stroke="#00f2fe" stroke-width="2"/>'
               '</g>')
    out.append("</svg>")
    return "".join(out)
