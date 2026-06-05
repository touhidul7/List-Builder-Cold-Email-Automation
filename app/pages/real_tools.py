"""Real provider tools page with approval-gated actions."""

import streamlit as st

from app.ui_helpers import page_intro, render_dataframe, success_box, warning_box
from app.utils import fetch_table, get_mandates_df
from scripts.config import get_settings
from scripts.export_to_smartlead import (
    SmartleadDraftCampaignRequest,
    create_smartlead_draft_campaign_real,
)
from scripts.run_apify_google_maps_real import (
    ApifyGoogleMapsRealRequest,
    run_apify_google_maps_real,
)
from scripts.run_apollo_search import (
    ApolloPeopleSearchRequest,
    run_apollo_people_search_real,
)


def _approved_approvals() -> list[str]:
    df = fetch_table(
        """
        SELECT id, provider, action_type, action_description
        FROM cost_approvals
        WHERE approval_status = 'approved'
        ORDER BY created_at DESC, rowid DESC
        """
    )
    return [] if df.empty else df["id"].tolist()


def _selected_mandate() -> str | None:
    mandates = get_mandates_df()
    if mandates.empty:
        warning_box("Create a mandate before running real provider tools.")
        return None
    return st.selectbox("Mandate", mandates["id"].tolist())


def _selected_approval() -> str | None:
    approvals = _approved_approvals()
    if not approvals:
        warning_box("Approve a cost approval before running real provider tools.")
        return None
    return st.selectbox("Approved cost approval", approvals)


def render() -> None:
    """Render approval-gated real provider controls."""
    st.title("Real Tools")
    page_intro(
        "Production workbench for external systems. Implemented actions are clickable; unimplemented SOP integrations are shown with the exact gate they still need."
    )
    st.error(
        "Real mode can spend credits or create external records. It requires DRY_RUN=false, "
        "REAL_API_CONFIRMATION=I_UNDERSTAND_REAL_API_CALLS, provider API keys, and an approved cost approval."
    )
    mandate_id = _selected_mandate()
    approval_id = _selected_approval()
    if not mandate_id or not approval_id:
        return

    settings = get_settings()
    tabs = st.tabs(
        [
            "Apollo",
            "Apify",
            "Smartlead",
            "Consulti",
            "Hunter",
            "MillionVerifier",
            "Winnr",
        ]
    )
    with tabs[0]:
        st.subheader("Apollo People Search")
        st.caption("Apollo People Search does not return emails. It imports people and companies for follow-up enrichment/review.")
        keywords = st.text_input("Keywords", "commercial cleaning")
        locations = st.text_input("Organization locations, comma-separated", "Ontario, Canada")
        titles = st.text_input("Person titles, comma-separated", "Owner, President, Founder")
        per_page = st.number_input("Results per page", min_value=1, max_value=100, value=25)
        if st.button("Run Real Apollo Search"):
            request = ApolloPeopleSearchRequest(
                mandate_id=mandate_id,
                approval_id=approval_id,
                q_keywords=keywords,
                organization_locations=[item.strip() for item in locations.split(",") if item.strip()],
                person_titles=[item.strip() for item in titles.split(",") if item.strip()],
                per_page=int(per_page),
            )
            result = run_apollo_people_search_real(request)
            success_box("Apollo search completed and imported into local SQLite.")
            st.json(result.model_dump())

    with tabs[1]:
        st.subheader("Apify Google Maps Task")
        st.caption("Requires APIFY_GOOGLE_MAPS_TASK_ID. The task input is actor-specific.")
        query = st.text_input("Search query", "commercial cleaning companies in Ontario")
        limit = st.number_input("Apify import limit", min_value=1, max_value=100, value=25)
        if st.button("Run Real Apify Task"):
            request = ApifyGoogleMapsRealRequest(
                mandate_id=mandate_id,
                approval_id=approval_id,
                query=query,
                limit=int(limit),
            )
            result = run_apify_google_maps_real(request)
            success_box("Apify task completed and imported into local SQLite.")
            st.json(result.model_dump())

    with tabs[2]:
        st.subheader("Smartlead Draft Campaign")
        st.caption("Creates a Smartlead draft campaign only. It does not add senders or start sending.")
        campaign_name = st.text_input("Campaign name")
        if st.button("Create Real Smartlead Draft"):
            request = SmartleadDraftCampaignRequest(
                mandate_id=mandate_id,
                approval_id=approval_id,
                campaign_name=campaign_name or None,
            )
            result = create_smartlead_draft_campaign_real(request)
            success_box("Smartlead draft campaign created.")
            st.json(result.model_dump())

        st.divider()
        st.subheader("Smartlead Lead Upload, Sequence Upload, Sender Assignment, Result Sync")
        st.warning(
            "Not implemented yet. The SOP requires approved-lead upload, merge-field mapping, sequence upload, sender assignment, and read-only result sync. Current real Smartlead support stops at draft campaign creation."
        )
        st.code(
            "Backend placeholders:\n"
            "scripts/upload_senders_to_smartlead.py\n"
            "scripts/sync_smartlead_results.py",
            language="text",
        )

    with tabs[3]:
        st.subheader("Consulti")
        st.caption("SOP role: B2B/local lead pull, enrichment, and primary email verification.")
        st.write(f"API key status: {'configured' if settings.consulti_api_key else 'missing'}")
        st.warning(
            "Not implemented yet. Build real Consulti lead-pull/enrichment/verification only after confirming provider endpoints, pricing, consent rules, and approval gating."
        )
        st.code(
            "Backend placeholders:\n"
            "scripts/run_consulti_b2b_search.py\n"
            "scripts/run_consulti_local_search.py\n"
            "scripts/verify_with_consulti.py",
            language="text",
        )

    with tabs[4]:
        st.subheader("Hunter")
        st.caption("SOP role: enrich only high-fit Google Maps leads that have a website and no email.")
        st.write(f"API key status: {'configured' if settings.hunter_api_key else 'missing'}")
        st.warning(
            "Not implemented yet. A production Hunter action must enforce: Google Maps source, missing email, website present, high fit score, cost approval, and duplicate check."
        )
        st.code("Backend placeholder:\nscripts/enrich_with_hunter.py", language="text")

    with tabs[5]:
        st.subheader("MillionVerifier")
        st.caption("SOP role: backup verification only if Consulti is unavailable.")
        st.write(f"API key status: {'configured' if settings.millionverifier_api_key else 'missing'}")
        st.warning(
            "Not implemented yet. A production backup verifier must preserve status rules: valid approved, catch_all manual review, risky/invalid/unknown excluded."
        )
        st.code("Backend placeholder:\nscripts/verify_with_millionverifier.py", language="text")

    with tabs[6]:
        st.subheader("Winnr Domains And Inboxes")
        st.caption("SOP role: purchase domains, create inboxes, track DNS/warmup, and prepare Smartlead senders.")
        st.write(
            f"API key/account status: {'configured' if settings.winnr_api_key and settings.winnr_account_email else 'missing'}"
        )
        st.warning(
            "Not implemented yet. Domain and inbox purchases create real charges, so this needs the strongest approval flow before any API call is added."
        )
        st.code(
            "Backend placeholders:\n"
            "scripts/winnr_purchase_domains.py\n"
            "scripts/winnr_create_inboxes.py\n"
            "scripts/upload_senders_to_smartlead.py",
            language="text",
        )

    render_dataframe(
        fetch_table(
            """
            SELECT id, provider, action_type, action_description, approval_status, approved_by
            FROM cost_approvals
            ORDER BY created_at DESC, rowid DESC
            """
        ),
        "Cost Approval Records",
    )
