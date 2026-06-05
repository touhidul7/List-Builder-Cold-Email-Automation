"""Dashboard page for the Streamlit frontend."""

import pandas as pd
import streamlit as st

from app.ui_helpers import (
    render_dataframe,
    render_metric_row,
    show_db_missing_warning,
    show_dry_run_banner,
    success_box,
)
from app.utils import (
    ensure_local_db_exists,
    get_campaigns_df,
    get_db_counts,
    get_mandates_df,
    get_source_runs_df,
    short_id,
)
from scripts.dry_pipeline import run_dry_pipeline


DEFAULT_PROMPT = "Find 25 acquisition targets for a client who wants to buy a commercial cleaning company in Ontario."


def _recent(df: pd.DataFrame, columns: list[str], limit: int = 5) -> pd.DataFrame:
    if df.empty:
        return df
    existing = [column for column in columns if column in df.columns]
    display_df = df.head(limit).copy()
    for column in ("id", "mandate_id", "smartlead_campaign_id"):
        if column in display_df.columns:
            display_df[column] = display_df[column].map(short_id)
    return display_df[existing]


def render() -> None:
    """Render dashboard overview and one-click dry pipeline."""
    st.title("Dashboard")
    show_dry_run_banner()
    if not ensure_local_db_exists():
        show_db_missing_warning()
        return

    counts = get_db_counts()
    render_metric_row(counts)

    with st.expander("Run Full Dry Pipeline", expanded=False):
        st.caption("Creates a local mock mandate, mock leads, scoring, research, email copy, and a paused mock campaign.")
        prompt = st.text_area("Mandate prompt", DEFAULT_PROMPT)
        limit = st.number_input("Lead limit", min_value=1, max_value=100, value=25)
        reset_db = st.checkbox("Reset local database first")
        if st.button("Run Full Dry Pipeline"):
            summary = run_dry_pipeline(prompt, limit=int(limit), reset_db=reset_db)
            st.session_state["current_mandate_id"] = summary.mandate_id
            success_box("Full dry pipeline completed. No external APIs were called.")
            st.json(summary.model_dump())

    mandates_df = get_mandates_df()
    source_runs_df = get_source_runs_df()
    campaigns_df = get_campaigns_df()
    render_dataframe(
        _recent(mandates_df, ["id", "mandate_name", "industry", "geography", "status", "created_at"]),
        "Recent Mandates",
    )
    render_dataframe(
        _recent(source_runs_df, ["id", "provider", "source_type", "query", "status", "records_imported", "created_at"]),
        "Recent Source Runs",
    )
    render_dataframe(
        _recent(campaigns_df, ["id", "mandate_id", "campaign_name", "smartlead_campaign_id", "campaign_status", "created_at"]),
        "Recent Campaigns",
    )

    st.subheader("Quick Workflow Guide")
    st.write(
        "1. Create mandate\n"
        "2. Import real lead CSV or review source runs\n"
        "3. Score leads\n"
        "4. Research Tier 1\n"
        "5. Generate email copy\n"
        "6. Create paused campaign review"
    )
