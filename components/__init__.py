"""UI components. Builders (*_html) are pure; render_* functions import streamlit lazily."""
import html as _html


def clean(markup: str) -> str:
    """Strip indentation and blank lines so Streamlit's markdown parser keeps the
    snippet as one raw-HTML block (4-space indents would become code blocks)."""
    return "\n".join(line.strip() for line in markup.splitlines() if line.strip())


def esc(text: str) -> str:
    """HTML-escape dynamic text; also neutralise markdown emphasis characters."""
    return _html.escape(str(text), quote=True).replace("_", "&#95;").replace("*", "&#42;")
