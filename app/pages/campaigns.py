"""Mock campaign page."""

import pandas as pd
import streamlit as st

from app.ui_helpers import render_dataframe, show_dry_run_banner, success_box, warning_box
from app.utils import fetch_table, get_campaigns_df, get_mandates_df, short_id

try:
    from scripts.mock_campaign_reporting import generate_mock_campaign_events
    from scripts.mock_smartlead_deploy import create_mock_smartlead_campaign
except ImportError:  # pragma: no cover - defensive optional backend handling
    generate_mock_campaign_events = None
    create_mock_smartlead_campaign = None


def _campaign_leads(mandate_id: str | None) -> pd.DataFrame:
    query = """
        SELECT
            contacts.email,
            companies.company_name,
            campaign_leads.upload_status,
            campaign_leads.approval_status,
            campaign_leads.created_at
        FROM campaign_leads
        JOIN campaigns ON campaigns.id = campaign_leads.campaign_id
        JOIN contacts ON contacts.id = campaign_leads.contact_id
        JOIN companies ON companies.id = contacts.company_id
    """
    params: tuple[str, ...] = ()
    if mandate_id:
        query += " WHERE campaigns.mandate_id = ?"
        params = (mandate_id,)
    query += " ORDER BY campaign_leads.created_at DESC, campaign_leads.rowid DESC"
    return fetch_table(query, params)


def render() -> None:
    """Render paused mock campaign actions and tables."""
    st.title("Campaigns")
    show_dry_run_banner()
    st.warning(
        "Campaign review is local/paused. No real Smartlead campaign is created, launched, or sent from this app."
    )
    mandates = get_mandates_df()
    options = ["All"] + ([] if mandates.empty else mandates["id"].tolist())
    selected = st.selectbox("Mandate", options)
    mandate_id = None if selected == "All" else selected
    limit = st.number_input("Lead upload limit", min_value=1, max_value=100, value=100)
    if st.button("Create Mock Smartlead Campaign"):
        if create_mock_smartlead_campaign is None:
            warning_box("Mock Smartlead backend module is not implemented yet.")
        elif not mandate_id:
            warning_box("Select a specific mandate before creating a mock campaign.")
        else:
            result = create_mock_smartlead_campaign(mandate_id, limit=int(limit))
            success_box("Paused mock campaign created/updated.")
            st.json(result.model_dump())

    campaigns = get_campaigns_df()
    if mandate_id and not campaigns.empty:
        campaigns = campaigns[campaigns["mandate_id"] == mandate_id]
    display_campaigns = campaigns.copy()
    if not display_campaigns.empty:
        display_campaigns["id"] = display_campaigns["id"].map(short_id)
        display_campaigns["mandate_id"] = display_campaigns["mandate_id"].map(short_id)
        display_campaigns = display_campaigns[
            ["id", "mandate_id", "campaign_name", "smartlead_campaign_id", "campaign_status", "created_at"]
        ]
    render_dataframe(display_campaigns, "Campaigns")
    render_dataframe(_campaign_leads(mandate_id), "Campaign Leads")

    if generate_mock_campaign_events is None or campaigns.empty:
        if generate_mock_campaign_events is None:
            warning_box("Mock campaign reporting backend module is not implemented yet.")
        return
    labels = {f"{short_id(row['id'])} | {row['campaign_name']}": row["id"] for _, row in campaigns.iterrows()}
    selected_campaign = st.selectbox("Campaign report target", list(labels.keys()))
    if st.button("Generate Mock Campaign Report"):
        summary = generate_mock_campaign_events(labels[selected_campaign])
        success_box("Mock reporting events generated.")
        st.json(summary.model_dump())
