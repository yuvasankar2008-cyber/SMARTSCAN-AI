"""SMARTSCAN-AI simulation progress panel.

This visualizes software-run completion only. It does not display
detection, interception, target activity, or scan-performance data.
"""

import streamlit as st
import streamlit.components.v1 as components


def render_simulation_progress(sim) -> None:
    """Render a slim, full-width progress panel below the radar/control row."""
    total = 100
    current = max(0, min(int(getattr(sim, "round", 0)), total))
    if current <= 0:
        return

    percent = current / total * 100
    # The plotted values represent completed simulation rounds only.
    # This is a neutral progress trace, not operational performance data.
    x0, x1 = 42, 958
    y_top, y_bottom = 35, 145
    x_now = x0 + (x1 - x0) * current / total
    y_now = y_bottom - (y_bottom - y_top) * percent / 100

    html = f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
* {{ box-sizing: border-box; }}
html, body {{
    margin: 0; padding: 0; background: transparent;
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif;
}}
.panel {{
    width: 100%; height: 224px; padding: 15px 20px 12px;
    border: 1px solid rgba(34, 211, 238, .27);
    border-radius: 12px;
    background: linear-gradient(115deg, #0c1527 0%, #101b30 55%, #0b1729 100%);
    box-shadow: inset 0 1px 0 rgba(148, 163, 184, .05),
                0 8px 24px rgba(0, 0, 0, .16);
    color: #e2e8f0;
}}
.head {{
    display: flex; justify-content: space-between; align-items: center;
    gap: 12px; margin-bottom: 4px;
}}
.title {{
    color: #e2e8f0; font-size: 12px; font-weight: 800;
    letter-spacing: .09em; text-transform: uppercase;
}}
.sub {{ color: #8293aa; font-size: 10px; margin-top: 3px; }}
.pill {{
    color: #67e8f9; border: 1px solid rgba(34,211,238,.35);
    background: rgba(6,182,212,.10); border-radius: 6px;
    padding: 5px 9px; font: 700 11px ui-monospace, monospace;
    white-space: nowrap;
}}
svg {{ width: 100%; height: 155px; display: block; }}
.axis {{ fill: #8293aa; font-size: 10px; }}
@media (max-width: 600px) {{
    .panel {{ padding: 12px; height: 210px; }}
    .title {{ font-size: 10px; }}
    .sub {{ font-size: 9px; }}
    svg {{ height: 145px; }}
}}
</style>
</head>
<body>
<div class="panel">
  <div class="head">
    <div>
      <div class="title">Simulation Execution Progress</div>
      <div class="sub">Software run completion · updates with each simulation round</div>
    </div>
    <div class="pill">{current} / {total} ROUNDS</div>
  </div>
  <svg viewBox="0 0 1000 180" preserveAspectRatio="none"
       role="img" aria-label="Simulation progress {percent:.0f} percent">
    <defs>
      <linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#22d3ee" stop-opacity=".25"/>
        <stop offset="100%" stop-color="#22d3ee" stop-opacity=".015"/>
      </linearGradient>
      <linearGradient id="line" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stop-color="#3b82f6"/>
        <stop offset="100%" stop-color="#22d3ee"/>
      </linearGradient>
    </defs>
    <g stroke="#26364d" stroke-width="1" stroke-dasharray="4 6">
      <line x1="42" y1="35" x2="958" y2="35"/>
      <line x1="42" y1="90" x2="958" y2="90"/>
      <line x1="42" y1="145" x2="958" y2="145"/>
    </g>
    <path d="M {x0} {y_bottom} L {x_now:.1f} {y_now:.1f} L {x_now:.1f} {y_bottom} Z"
          fill="url(#fill)"/>
    <line x1="{x0}" y1="{y_bottom}" x2="{x1}" y2="{y_bottom}"
          stroke="#34465f" stroke-width="1"/>
    <line x1="{x0}" y1="{y_bottom}" x2="{x_now:.1f}" y2="{y_now:.1f}"
          stroke="url(#line)" stroke-width="3" stroke-linecap="round"/>
    <circle cx="{x_now:.1f}" cy="{y_now:.1f}" r="5"
            fill="#22d3ee" stroke="#dffaff" stroke-width="2"/>
    <text x="42" y="169" class="axis">ROUND 0</text>
    <text x="500" y="169" text-anchor="middle" class="axis">SIMULATION PROGRESS</text>
    <text x="958" y="169" text-anchor="end" class="axis">ROUND 100</text>
  </svg>
</div>
</body>
</html>
"""
    # Use an iframe so Streamlit's Markdown parser cannot show the HTML as code.
    components.html(html, height=232, scrolling=False)
