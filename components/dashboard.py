"""Hero section with the live KPI banner, plus the analytics/formulation section."""
from components import clean


def _kpi(label: str, value: str, caption: str, tone: str, val_id: str) -> str:
    return (f'<div class="ss-kpi ss-kpi-{tone}">'
            f'<div class="ss-kpi-label">{label}</div>'
            f'<div class="ss-kpi-value c-{tone}" id="{val_id}">{value}</div>'
            f'<div class="ss-kpi-cap">{caption}</div></div>')


def hero_html(kpis: dict) -> str:
    cards = "".join([
        _kpi("Probability of Detection (Pd)", kpis["pd"], "+16.9% vs Conventional", "cyan", "kpi-comp"),
        _kpi("Probability of False Alarm (Pfa)", kpis["pfa"], "-36.0% Less False Alarms", "purple", "kpi-idle"),
        _kpi("Average Reward (R̄)", kpis["avg_reward"], "Points per Round", "blue", "kpi-reward"),
        _kpi("Correct Prediction Pct", kpis["accuracy"], "Decision Accuracy", "amber", "kpi-eff"),
    ])
    return clean(f"""
<div class="ss-card ss-hero ss-anchor" id="mission-control">
<div class="ss-glow ss-glow-br"></div>
<div class="ss-glow ss-glow-tl"></div>
<div class="ss-hero-grid">
<div class="ss-hero-main">
<div class="ss-badge-team"><span>Team AetherX</span><span>•</span><span>Smart India Hackathon 2026</span></div>
<div class="ss-h1" role="heading" aria-level="1">Autonomous <span class="neon-text">Adaptive Scan Scheduling</span> for Robotic Surveillance</div>
<div class="ss-lead">Demonstrating how multi-armed bandit optimization (UCB1) with priority utility and staleness tracking
outperforms static round-robin scheduling by over <b>+36% efficiency gain</b> under observation resource constraints.</div>
<div class="ss-cta">
<a href="#simulation-suite" class="ss-cta-primary"> Launch Interactive Simulation</a>
<a href="#presentation-deck" class="ss-cta-secondary"> View SIH Pitch Deck</a>
</div>
</div>
<div class="ss-kpi-grid">{cards}</div>
</div>
</div>
""")


def analytics_html() -> str:
    return clean("""
<div class="ss-card ss-analytics ss-anchor" id="analytics-section">
<div class="ss-section-head">
<div>
<div class="ss-h2" role="heading" aria-level="2">Adaptive Learning vs Static Baseline Engine</div>
<div class="ss-sub">Mathematical formulation and real-time decision mechanics</div>
</div>
<span class="ss-chip-cyan">Explainable AI</span>
</div>
<div class="ss-two-col">
<div class="ss-formula-box">
<div class="ss-formula-label">Composite Decision Formula:</div>
<div class="ss-formula">
<b>Score<sub>i</sub>(t)</b> = (p̂<sub>i</sub> · W<sub>i</sub> · 10) + c · √(2·ln(t)/N<sub>i</sub>) + γ · Staleness<sub>i</sub> · (W<sub>i</sub>/2)
</div>
<div class="ss-formula-notes">
<div>• <b>p̂<sub>i</sub></b>: Empirical probability of activity (Laplace smoothed: (D<sub>i</sub>+1)/(N<sub>i</sub>+2))</div>
<div>• <b>W<sub>i</sub></b>: Priority weight (Alpha: 3.0, Delta: 4.0, Charlie: 1.0)</div>
<div>• <b>c · √(2·ln(t)/N<sub>i</sub>)</b>: Upper Confidence Bound (UCB1) exploration bonus</div>
<div>• <b>Staleness<sub>i</sub></b>: Rounds since last observation (guarantees anti-starvation)</div>
</div>
</div>
<div class="ss-highlights">
<div class="ss-hl ss-hl-purple">
<div class="ss-hl-title">1. Autonomous Preference Shifting</div>
<div class="ss-hl-text">Unlike Round-Robin which visits every sector 20% of the time, the adaptive scheduler concentrates
over 45% of limited observation capacity on high-activity, high-priority sectors.</div>
</div>
<div class="ss-hl ss-hl-cyan">
<div class="ss-hl-title">2. Sudden Surge Detection</div>
<div class="ss-hl-text">Using Exponentially Weighted Moving Averages (EWMA), when a previously quiet sector (like Delta)
spikes into critical burst activity, the engine responds within 2 rounds.</div>
</div>
<div class="ss-hl ss-hl-emerald">
<div class="ss-hl-title">3. Zero Starvation Guarantee</div>
<div class="ss-hl-text">The staleness multiplier ensures that low-probability background channels (like Charlie) are periodically
checked, ensuring no spatial sector remains permanently blind.</div>
</div>
</div>
</div>
</div>
""")


def render_hero(kpis: dict) -> None:
    import streamlit as st
    st.markdown(hero_html(kpis), unsafe_allow_html=True)


def render_analytics() -> None:
    import streamlit as st
    st.markdown(analytics_html(), unsafe_allow_html=True)
