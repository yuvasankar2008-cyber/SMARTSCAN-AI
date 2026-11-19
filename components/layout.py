"""Top navigation bar and footer (static markup, same content as the original)."""
from components import clean


def header_html() -> str:
    return clean("""
<div class="ss-header">
<div class="ss-header-inner">
<div class="ss-brand">
<div class="ss-logo"><div class="ss-logo-inner">📡</div></div>
<div>
<span class="ss-title">SMARTSCAN <span class="c-cyan">AI</span></span>
<span class="ss-sih-chip">SIH 2026 #SIH26055</span>
</div>
</div>
<div class="ss-nav">
    <a href="#mission-control">Mission Control</a>
    <a href="#simulation-suite">Radar & Simulation</a>
    <a href="#analytics-section">Analytics</a>
    <a href="#presentation-deck">Pitch Deck</a>
    <a href="#about-section">About</a>
</div>
<div class="ss-header-right">
<div class="ss-online"><span class="ss-dot live-pulse"></span><span>ONLINE</span></div>
<a href="http://localhost:8501" target="_blank" class="ss-dash-link"><span>Streamlit Dashboard</span><span>↗</span></a>
</div>
</div>
</div>
""")


def footer_html() -> str:
    return clean("""
<div class="ss-footer" id="about-section">
<div class="ss-footer-inner">
<div><span class="ss-footer-brand">SMARTSCAN AI</span> • Smart India Hackathon 2026 (Problem ID: SIH26055)</div>
<div>Designed for Team AetherX • Abstract Educational Software Prototype</div>
</div>
</div>
""")
