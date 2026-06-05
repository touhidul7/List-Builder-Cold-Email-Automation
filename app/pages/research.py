"""Mock research and personalization page."""

import pandas as pd
import streamlit as st

from app.ui_helpers import render_dataframe, show_dry_run_banner, success_box, warning_box
from app.utils import fetch_table, get_mandates_df
from scripts.research_best_leads import research_tier_one_leads


def render() -> None:
    """Render mock Tier 1 research action and personalization records."""
    st.title("Research")
    show_dry_run_banner()
    mandates = get_mandates_df()
    if mandates.empty:
        warning_box("No mandates found.")
        return
    mandate_id = st.selectbox("Mandate", mandates["id"].tolist())
    include_tier_two = st.checkbox("Include Tier 2")
    limit = st.number_input("Limit", min_value=1, max_value=100, value=25)
    if st.button("Research Tier 1 Mock"):
        results = research_tier_one_leads(
            mandate_id=mandate_id,
            limit=int(limit),
            include_tier_two=include_tier_two,
        )
        success_box(f"Created {len(results)} mock research records.")
        render_dataframe(pd.DataFrame([result.model_dump() for result in results]), "Research Results")

    personalization = fetch_table(
        """
        SELECT
            companies.company_name,
            contacts.full_name,
            contacts.email,
            personalization.opening_line,
            personalization.fit_rationale,
            personalization.outreach_angle,
            personalization.suggested_cta,
            personalization.created_at
        FROM personalization
        JOIN contacts ON contacts.id = personalization.contact_id
        JOIN companies ON companies.id = contacts.company_id
        WHERE companies.mandate_id = ?
        ORDER BY personalization.created_at DESC, personalization.rowid DESC
        """,
        (mandate_id,),
    )
    render_dataframe(personalization, "Personalization Records")
