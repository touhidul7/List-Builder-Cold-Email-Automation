"""Streamlit entrypoint for the local ListBuilder + ColdEmail AI dashboard."""

from pathlib import Path
import sys

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.pages import (  # noqa: E402
    campaigns,
    cost_approvals,
    dashboard,
    email_copy,
    leads,
    new_mandate,
    production_readiness,
    real_data_import,
    real_tools,
    research,
    scoring,
    settings,
    source_runs,
)
from app.ui_helpers import apply_app_style  # noqa: E402


PAGES = {
    "Dashboard": ("dashboard", dashboard.render),
    "Production Readiness": ("production-readiness", production_readiness.render),
    "New Mandate": ("new-mandate", new_mandate.render),
    "Source Runs": ("source-runs", source_runs.render),
    "Cost Approvals": ("cost-approvals", cost_approvals.render),
    "Real Data Import": ("real-data-import", real_data_import.render),
    "Real Tools": ("real-tools", real_tools.render),
    "Leads": ("leads", leads.render),
    "Scoring": ("scoring", scoring.render),
    "Research": ("research", research.render),
    "Email Copy": ("email-copy", email_copy.render),
    "Campaigns": ("campaigns", campaigns.render),
    "Settings": ("settings", settings.render),
}


def _run_navigation() -> None:
    """Use modern Streamlit navigation when available, otherwise radio pages."""
    if hasattr(st, "navigation") and hasattr(st, "Page"):
        pages = [
            st.Page(func, title=title, url_path=path)
            for title, (path, func) in PAGES.items()
        ]
        selected = st.navigation(pages)
        selected.run()
        return

    selected_title = st.sidebar.radio("Navigation", list(PAGES.keys()))
    PAGES[selected_title][1]()


def main() -> None:
    """Render the Streamlit app."""
    st.set_page_config(page_title="ListBuilder + ColdEmail AI", layout="wide")
    apply_app_style()
    st.sidebar.title("ListBuilder + ColdEmail AI")
    st.sidebar.caption("Deal origination workflow")
    st.sidebar.success("DRY RUN MODE")
    if st.sidebar.button("Refresh"):
        st.rerun()
    _run_navigation()


if __name__ == "__main__":
    main()
