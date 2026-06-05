"""Lead scoring page."""

import pandas as pd
import streamlit as st

from app.ui_helpers import render_dataframe, show_dry_run_banner, success_box, warning_box
from app.utils import fetch_table, get_companies_df, get_mandates_df
from scripts.score_leads import score_companies_for_mandate


def render() -> None:
    """Render scoring action and persisted lead score records."""
    st.title("Scoring")
    show_dry_run_banner()
    mandates = get_mandates_df()
    if mandates.empty:
        warning_box("No mandates found.")
        return
    mandate_id = st.selectbox("Mandate", mandates["id"].tolist())
    companies = get_companies_df(mandate_id)
    if companies.empty:
        warning_box("No companies exist for the selected mandate.")
    if st.button("Score Leads"):
        scores = score_companies_for_mandate(mandate_id)
        success_box(f"Scored {len(scores)} companies.")
        render_dataframe(pd.DataFrame([score.model_dump() for score in scores]), "Score Results")

    score_rows = fetch_table(
        """
        SELECT
            companies.company_name,
            lead_scores.total_score,
            lead_scores.priority_tier,
            lead_scores.icp_fit,
            lead_scores.geography_fit,
            lead_scores.company_size_fit,
            lead_scores.contact_quality,
            lead_scores.email_quality,
            lead_scores.source_confidence,
            lead_scores.strategic_relevance,
            lead_scores.score_reason
        FROM lead_scores
        JOIN companies ON companies.id = lead_scores.company_id
        WHERE companies.mandate_id = ?
        ORDER BY lead_scores.total_score DESC, companies.company_name
        """,
        (mandate_id,),
    )
    render_dataframe(score_rows, "Stored Lead Scores")
