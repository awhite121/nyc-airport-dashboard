from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parent
DASHBOARD_PATH = ROOT / "dashboard" / "when-to-leave-nyc-dashboard.html"

st.set_page_config(
    page_title="When to Leave NYC",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      #MainMenu, footer, header { visibility: hidden; }
      [data-testid="stAppViewContainer"] { background: #07111f; }
      [data-testid="stMainBlockContainer"] {
        max-width: 100%;
        padding: 0;
      }
      [data-testid="stVerticalBlock"] { gap: 0; }
      .stApp { overflow-x: hidden; }
      iframe {
        border: 0 !important;
        width: 100% !important;
        background: #07111f;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

if not DASHBOARD_PATH.exists():
    st.error(
        "Dashboard file not found at "
        f"`{DASHBOARD_PATH.relative_to(ROOT)}`. Make sure the `dashboard/` folder was committed."
    )
    st.stop()

try:
    dashboard_html = DASHBOARD_PATH.read_text(encoding="utf-8")
except OSError as exc:
    st.error(f"The dashboard could not be loaded: {exc}")
    st.stop()

components.html(dashboard_html, height=1600, scrolling=True)
