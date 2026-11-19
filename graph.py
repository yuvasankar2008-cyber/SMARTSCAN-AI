"""Safe, non-operational simulation progress visualization.

Shows only how far the software simulation has progressed. It does not
visualize detection, interception, target activity, or scan performance.
"""

import streamlit as st


def render_simulation_progress(sim) -> None:
    """Render a progress graph after at least one simulation round."""
    if sim.round <= 0:
        return

    completed = min(int(sim.round), 100)
    progress = [round((i / 100) * 100, 1) for i in range(completed + 1)]

    with st.container(key="progress_graph_card"):
        st.markdown(
            '<div class="ss-progress-graph-head">'
            '<div>'
            '<div class="ss-progress-graph-title">SIMULATION EXECUTION PROGRESS</div>'
            '<div class="ss-progress-graph-sub">Live run status · software simulation only</div>'
            '</div>'
            f'<div class="ss-progress-graph-value">{completed}%</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.area_chart(
            {"Completion (%)": progress},
            height=220,
            color="#22d3ee",
        )
        st.caption(f"{completed} of 100 simulation rounds completed")
