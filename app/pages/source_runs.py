"""Source runs page."""

import pandas as pd
import streamlit as st

from app.ui_helpers import render_dataframe, show_dry_run_banner, success_box, warning_box
from app.utils import get_mandates_df, get_source_runs_df, short_id
from scripts.run_apify_google_maps import run_apify_google_maps_mock


def _mandate_options() -> list[str]:
    df = get_mandates_df()
    return [] if df.empty else df["id"].tolist()


def render() -> None:
    """Render source run review and mock Google Maps action."""
    st.title("Source Runs")
    show_dry_run_banner()
    mandates = _mandate_options()
    selected_mandate = st.selectbox("Mandate", ["All"] + mandates)
    mandate_id = None if selected_mandate == "All" else selected_mandate
    runs_df = get_source_runs_df(mandate_id)
    display_df = runs_df.copy()
    if not display_df.empty:
        display_df["short_id"] = display_df["id"].map(short_id)
        display_df = display_df[
            ["short_id", "provider", "source_type", "query", "status", "estimated_cost", "records_found", "records_imported", "created_at"]
        ]
    render_dataframe(display_df, "Source Runs")

    st.warning("This is mock only. No real Apify API call will be made.")
    if runs_df.empty:
        return
    labels = {
        f"{short_id(row['id'])} | {row['provider']} | {row['source_type']}": row
        for _, row in runs_df.iterrows()
    }
    selected_label = st.selectbox("Select source run", list(labels.keys()))
    source_run = labels[selected_label]
    source_identity = f"{source_run['provider']} {source_run['source_type']}".lower()
    limit = st.number_input("Mock import limit", min_value=1, max_value=100, value=25)
    if "apify" in source_identity and "maps" in source_identity:
        if st.button("Run Google Maps Mock"):
            summary = run_apify_google_maps_mock(
                source_run["mandate_id"],
                source_run["id"],
                source_run["query"],
                limit=int(limit),
            )
            success_box("Mock Google Maps run completed.")
            st.json(summary)
    else:
        warning_box("Selected run is not an Apify Google Maps source run.")

    if st.button("Refresh Source Runs"):
        st.rerun()
