"""Mandate creation page."""

import pandas as pd
import streamlit as st

from app.ui_helpers import render_dataframe, show_dry_run_banner, success_box
from scripts.check_existing_leads import check_existing_leads
from scripts.icp_builder import build_icp
from scripts.mandate_intake import parse_mandate
from scripts.mandate_store import save_mandate
from scripts.source_planner import build_source_plan
from scripts.source_run_planner import create_source_runs_for_mandate


DEFAULT_PROMPT = "Find 25 acquisition targets for a client who wants to buy a commercial cleaning company in Ontario."


def _dict_table(data: dict) -> pd.DataFrame:
    return pd.DataFrame([{"field": key, "value": value} for key, value in data.items()])


def render() -> None:
    """Render mandate parsing and creation controls."""
    st.title("New Mandate")
    show_dry_run_banner()
    prompt = st.text_area("Mandate prompt", DEFAULT_PROMPT, height=120)
    run_existing = st.checkbox("Run existing lead check", value=True)
    create_runs = st.checkbox("Create source runs and cost approval records", value=True)

    if st.button("Parse Mandate"):
        mandate = parse_mandate(prompt)
        icp = build_icp(mandate)
        source_plan = build_source_plan(mandate, icp)
        render_dataframe(_dict_table(mandate.model_dump()), "Mandate")
        render_dataframe(_dict_table(icp.model_dump()), "ICP Summary")
        render_dataframe(
            pd.DataFrame([step.model_dump() for step in source_plan.source_steps]),
            "Source Plan",
        )
        if source_plan.warnings:
            st.warning("\n".join(source_plan.warnings))

    if st.button("Create Mandate Plan"):
        mandate = parse_mandate(prompt)
        mandate_id = save_mandate(mandate)
        st.session_state["current_mandate_id"] = mandate_id
        success_box(f"Created mandate: {mandate_id}")
        if run_existing:
            summary = check_existing_leads(
                mandate.industry,
                mandate.geography,
                mandate_id=mandate_id,
            )
            render_dataframe(_dict_table(summary.model_dump()), "Existing Lead Summary")
        if create_runs:
            runs = create_source_runs_for_mandate(mandate_id)
            render_dataframe(
                pd.DataFrame([run.model_dump() for run in runs]),
                "Planned Source Runs",
            )
            pending = [run for run in runs if run.approval_status == "pending"]
            st.caption(f"Pending approval records created: {len(pending)}")
