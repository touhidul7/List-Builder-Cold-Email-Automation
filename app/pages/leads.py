"""Lead browser and optional mock enrichment/verification page."""

import pandas as pd
import streamlit as st

from app.ui_helpers import render_dataframe, show_dry_run_banner, success_box
from app.utils import get_companies_df, get_contacts_df, get_mandates_df
from scripts.mock_email_enrichment import enrich_companies_without_contacts
from scripts.mock_email_verification import verify_contacts_mock


def _select_mandate() -> str | None:
    mandates = get_mandates_df()
    options = ["All"] + ([] if mandates.empty else mandates["id"].tolist())
    selected = st.selectbox("Mandate", options)
    return None if selected == "All" else selected


def render() -> None:
    """Render real lead tables and optional mock enrichment actions."""
    st.title("Leads")
    show_dry_run_banner()
    st.caption("Real imported companies and contacts appear here. Mock actions are optional helpers for dry-run demos.")
    mandate_id = _select_mandate()
    limit = st.number_input("Action limit", min_value=1, max_value=100, value=25)
    col1, col2 = st.columns(2)
    if col1.button("Run Mock Enrichment"):
        contacts = enrich_companies_without_contacts(mandate_id=mandate_id, limit=int(limit))
        success_box(f"Created {len(contacts)} mock contacts.")
        render_dataframe(pd.DataFrame([contact.model_dump() for contact in contacts]), "Mock Enrichment Results")
    if col2.button("Run Mock Verification"):
        results = verify_contacts_mock(mandate_id=mandate_id, limit=int(limit))
        success_box(f"Verified {len(results)} contacts locally.")
        render_dataframe(pd.DataFrame([result.model_dump() for result in results]), "Mock Verification Results")

    companies = get_companies_df(mandate_id)
    contacts = get_contacts_df(mandate_id)
    tabs = st.tabs(["Companies", "Contacts", "Valid Emails", "Tier 1 Leads"])
    with tabs[0]:
        columns = ["company_name", "website", "city", "province", "country", "phone", "source", "fit_score", "priority_tier"]
        render_dataframe(companies[[column for column in columns if column in companies.columns]] if not companies.empty else companies, "Companies")
    with tabs[1]:
        columns = ["company_name", "full_name", "title", "email", "email_status", "verification_provider", "previously_contacted"]
        render_dataframe(contacts[[column for column in columns if column in contacts.columns]] if not contacts.empty else contacts, "Contacts")
    with tabs[2]:
        valid = contacts[contacts["email_status"] == "valid"] if not contacts.empty and "email_status" in contacts.columns else contacts
        render_dataframe(valid, "Valid Emails")
    with tabs[3]:
        tier_1 = companies[companies["priority_tier"] == "Tier 1"] if not companies.empty and "priority_tier" in companies.columns else companies
        render_dataframe(tier_1, "Tier 1 Leads")
