"""Compact software-run progress panel; displays completion only."""
import streamlit.components.v1 as components
from simulation import TOTAL_ROUNDS


def render_simulation_progress(sim) -> None:
    current = max(0, min(int(getattr(sim, "round", 0)), TOTAL_ROUNDS))
    percent = current / TOTAL_ROUNDS * 100
    milestones = []
    for value in (0, 25, 50, 75, 100):
        left = value
        reached = percent >= value
        milestones.append(
            f'<span class="milestone {"done" if reached else ""}" style="left:{left}%">'
            f'<i></i><small>{value}%</small></span>'
        )
    html = f"""<!doctype html><html><head><meta charset="utf-8"><style>
    *{{box-sizing:border-box}}html,body{{margin:0;padding:0;background:transparent;
    font-family:Inter,ui-sans-serif,system-ui,Segoe UI,sans-serif}}
    .panel{{height:112px;padding:13px 18px 10px;border:1px solid rgba(34,211,238,.25);
    border-radius:12px;background:linear-gradient(110deg,#0c1527,#101b30 58%,#0b1729);
    color:#e2e8f0;box-shadow:inset 0 1px 0 rgba(148,163,184,.05)}}
    .head{{display:flex;justify-content:space-between;align-items:center;gap:10px}}
    .title{{font-size:11px;font-weight:800;letter-spacing:.09em;text-transform:uppercase}}
    .sub{{font-size:9px;color:#8293aa;margin-top:3px}}
    .count{{font:700 11px ui-monospace,monospace;color:#67e8f9;padding:5px 8px;
    border:1px solid rgba(34,211,238,.3);border-radius:6px;background:rgba(6,182,212,.08)}}
    .track{{position:relative;height:8px;margin:21px 5px 0;background:#26364d;border-radius:99px}}
    .fill{{height:100%;width:{percent:.2f}%;border-radius:99px;background:linear-gradient(90deg,#3b82f6,#22d3ee);
    box-shadow:0 0 12px rgba(34,211,238,.28);transition:width .25s ease}}
    .milestone{{position:absolute;top:-5px;transform:translateX(-50%);display:flex;align-items:center;flex-direction:column}}
    .milestone i{{width:9px;height:9px;border-radius:50%;background:#475569;border:2px solid #0c1527}}
    .milestone.done i{{background:#22d3ee;box-shadow:0 0 8px rgba(34,211,238,.6)}}
    .milestone small{{font-size:8px;color:#8293aa;margin-top:8px}}
    .foot{{display:flex;justify-content:space-between;margin-top:5px;font-size:9px;color:#8293aa}}
    @media(max-width:600px){{.panel{{height:108px;padding:11px 12px}}.title{{font-size:10px}}}}
    </style></head><body><div class="panel"><div class="head"><div><div class="title">Simulation Progress</div>
    <div class="sub">Software execution completion · not a performance or interception metric</div></div>
    <div class="count">{current} / {TOTAL_ROUNDS} ROUNDS</div></div>
    <div class="track"><div class="fill"></div>{''.join(milestones)}</div>
    <div class="foot"><span>START</span><span>{percent:.0f}% COMPLETE</span><span>FINISH</span></div>
    </div></body></html>"""
    components.html(html, height=118, scrolling=False)
