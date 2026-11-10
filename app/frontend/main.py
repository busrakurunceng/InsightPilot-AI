
"""InsightPilot AI multi-page Streamlit entry point."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st


st.set_page_config(
    page_title="InsightPilot AI",
    page_icon="📊",
    layout="wide",
)

pages = [
    st.Page(
        "dashboard.py",
        title="Business Dashboard",
        icon="📊",
        default=True,
    ),
    st.Page(
        "chat.py",
        title="Conversational BI",
        icon="💬",
    ),
]

navigation = st.navigation(
    pages,
    position="sidebar",
)

navigation.run()
