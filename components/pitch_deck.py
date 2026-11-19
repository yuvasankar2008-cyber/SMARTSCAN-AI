"""Five-slide educational project overview. Prev/Next use Streamlit session state."""
from components import clean, esc

SLIDES = [
    {"tag": "SLIDE 1: THE CHALLENGE", "title": "Understanding Limited Observation in Synthetic Environments",
     "content": "The prototype demonstrates a fictional environment containing multiple abstract sectors and a limited number of observations per simulation round. The interface makes the constraints and recorded outcomes visible."},
    {"tag": "SLIDE 2: THE PROTOTYPE", "title": "A Python-Based Adaptive Simulation Demonstrator",
     "content": "SMARTSCAN AI provides a software-only demonstration with synthetic activity labels, selectable scenarios, a radar-style visual, progress tracking and experiment summaries. It is not connected to real sensors or emitters."},
    {"tag": "SLIDE 3: TRANSPARENT REPORTING", "title": "Metrics With Explicit Definitions and Limitations",
     "content": "The dashboard reports synthetic false-alarm probability, active-episode intercept rate, intercept time error and classification accuracy. Every metric is calculated from generated outcomes and prior observations."},
    {"tag": "SLIDE 4: EXPERIMENT VISUALISATION", "title": "Heatmaps, Scenario Profiles and Experiment History",
     "content": "Recorded observations are displayed in a time-sector heatmap. Scenario profiles show expected synthetic activity patterns, while saved snapshots make separate demonstration runs easier to review."},
    {"tag": "SLIDE 5: SCOPE & FUTURE WORK", "title": "A Reproducible Educational Software Prototype",
     "content": "The current deliverable is a fictional, non-operational simulation. Its results should not be interpreted as validated real-world detection, interception, sensor or deployment performance."},
]


def slide_html(index: int) -> str:
    s = SLIDES[index % len(SLIDES)]
    return clean(
        f'<div class="ss-slide"><div class="ss-slide-tag">{esc(s["tag"])}</div>'
        f'<div class="ss-slide-title">{esc(s["title"])}</div>'
        f'<div class="ss-slide-text">{esc(s["content"])}</div></div>'
    )


def head_html() -> str:
    return clean(
        '<div class="ss-anchor" id="presentation-deck"><span class="ss-eyebrow">Project Overview</span>'
        '<div class="ss-h2" role="heading" aria-level="2">SMARTSCAN AI Demonstration Deck</div></div>'
    )


def slide_counter_html(index: int) -> str:
    return f'<div class="ss-slide-num">{index % len(SLIDES) + 1} / {len(SLIDES)}</div>'


def _next():
    import streamlit as st
    st.session_state.slide = (st.session_state.slide + 1) % len(SLIDES)


def _prev():
    import streamlit as st
    st.session_state.slide = (st.session_state.slide - 1) % len(SLIDES)


def render_pitch_deck() -> None:
    import streamlit as st

    @st.fragment
    def deck():
        i = st.session_state.slide
        with st.container(key="deck_card"):
            with st.container(key="deck_head"):
                c_title, c_prev, c_num, c_next = st.columns([6, 1.3, 0.9, 1.3])
                c_title.markdown(head_html(), unsafe_allow_html=True)
                c_prev.button("◀ Prev", key="deck_prev", on_click=_prev)
                c_num.markdown(slide_counter_html(i), unsafe_allow_html=True)
                c_next.button("Next ▶", key="deck_next", on_click=_next)
            st.markdown(slide_html(i), unsafe_allow_html=True)

    deck()
