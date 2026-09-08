from __future__ import annotations

import streamlit as st

try:
    from .data import load_dashboard_tables
except ImportError:
    from data import load_dashboard_tables


@st.cache_resource(show_spinner=False)
def load_cached_dashboard_tables() -> dict:
    """Load the read-only dashboard frames once per Streamlit process."""
    return load_dashboard_tables()
