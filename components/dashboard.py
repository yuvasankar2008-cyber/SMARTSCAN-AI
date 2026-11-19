"""Hero KPIs and metric definitions, styled to match the original portal."""
from components import clean


def _kpi(label: str, value: str, caption: str, tone: str, val_id: str) -> str:
    return (f'<div class="ss-kpi ss-kpi-{tone}">'
            f'<div class="ss-kpi-label">{label}</div>'
            f'<div class="ss-kpi-value c-{tone}" id="{val_id}">{value}</div>'
            f'<div class="ss-kpi-cap">{caption}</div></div>')


def hero_html(kpis: dict) -> str:
    cards = "".join([
        _kpi("Synthetic Probability of Detection", kpis["pd"], "Observed active events / all active events", "cyan", "kpi-comp"),
        _kpi("False Alarm Probability", kpis["pfa"], "Unavailable: no false-positive sensor model", "purple", "kpi-idle"),
        _kpi("Average Simulation Reward", kpis["avg_reward"], "Cumulative reward / completed rounds", "blue", "kpi-reward"),
        _kpi("Observed Active Yield", kpis["observed_yield"], "Active observations / total observations", "amber", "kpi-eff"),
    ])
    return clean(f"""
<div class="ss-card ss-hero ss-anchor" id="mission-control">
<div class="ss-glow ss-glow-br"></div><div class="ss-glow ss-glow-tl"></div>
<div class="ss-hero-grid"><div class="ss-hero-main">
<div class="ss-badge-team"><span>Team AetherX</span><span>•</span><span>Smart India Hackathon 2026</span></div>
<div class="ss-h1" role="heading" aria-level="1">SMARTSCAN <span class="neon-text">Synthetic Scan Simulation</span></div>
<div class="ss-lead">An educational software prototype for exploring fictional sector activity, simulation progress and transparent experiment reporting. All displayed activity is synthetic.</div>
<div class="ss-cta"><a href="#simulation-suite" class="ss-cta-primary">Launch Simulation</a>
<a href="#presentation-deck" class="ss-cta-secondary">View Project Deck</a></div>
</div><div class="ss-kpi-grid">{cards}</div></div></div>
""")


def analytics_html() -> str:
    return clean("""
<div class="ss-card ss-analytics ss-anchor" id="analytics-section">
<div class="ss-section-head"><div><div class="ss-h2" role="heading" aria-level="2">Metric Definitions &amp; Simulation Scope</div>
<div class="ss-sub">Transparent reporting for synthetic observations</div></div><span class="ss-chip-cyan">Explainable Results</span></div>
<div class="ss-two-col"><div class="ss-formula-box"><div class="ss-formula-label">Reported metric definitions</div>
<div class="ss-formula"><b>Pd</b> = observed active events ÷ all synthetic active events</div>
<div class="ss-formula"><b>Observed active yield</b> = active observations ÷ total observations</div>
<div class="ss-formula-notes"><div>• Average reward = cumulative simulation reward ÷ completed rounds.</div>
<div>• Pfa is not calculated because the prototype has no false-positive sensor model.</div>
<div>• Observed active yield is not prediction accuracy.</div></div></div>
<div class="ss-highlights"><div class="ss-hl ss-hl-purple"><div class="ss-hl-title">Synthetic ground truth</div>
<div class="ss-hl-text">The environment generates fictional active/inactive labels. Unobserved active events count as not observed when calculating the synthetic detection fraction.</div></div>
<div class="ss-hl ss-hl-cyan"><div class="ss-hl-title">No unsupported claims</div>
<div class="ss-hl-text">The dashboard does not claim measured false-alarm reduction, real-world interception performance or a validated advantage over another scheduler.</div></div>
<div class="ss-hl ss-hl-emerald"><div class="ss-hl-title">Prototype boundary</div>
<div class="ss-hl-text">This project is a fictional, non-operational software demonstration. Its metrics describe only the included synthetic data.</div></div></div></div></div>
""")


def render_hero(kpis: dict) -> None:
    import streamlit as st
    st.markdown(hero_html(kpis), unsafe_allow_html=True)


def render_analytics() -> None:
    import streamlit as st
    st.markdown(analytics_html(), unsafe_allow_html=True)
