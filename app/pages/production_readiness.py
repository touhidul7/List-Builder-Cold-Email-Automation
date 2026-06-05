"""Production readiness and SOP coverage page."""

import pandas as pd
import streamlit as st

from app.ui_helpers import page_intro, render_dataframe, status_label
from scripts.config import get_settings
from scripts.production_readiness import get_readiness_items, summarize_readiness


def _readiness_df() -> pd.DataFrame:
    """Return display rows for the SOP readiness matrix."""
    rows = []
    for item in get_readiness_items():
        rows.append(
            {
                "Area": item.area,
                "Status": item.status,
                "Surfaces": ", ".join(item.surfaces),
                "Requirement": item.requirement,
                "Evidence": item.evidence,
                "Next Step": item.next_step,
            }
        )
    return pd.DataFrame(rows)


def _status_filter_options(df: pd.DataFrame) -> list[str]:
    """Return stable status filter choices."""
    return ["All"] + [status for status in ("done", "partial", "missing", "blocked") if status in set(df["Status"])]


def render() -> None:
    """Render the production readiness page."""
    st.title("Production Readiness")
    page_intro(
        "A read-only SOP checklist for what is working, what is safely gated, and what still needs provider-specific build work."
    )

    settings = get_settings()
    items = get_readiness_items(settings)
    summary = summarize_readiness(items)
    metric_cols = st.columns(4)
    metric_cols[0].metric("Done", summary["done"])
    metric_cols[1].metric("Partial", summary["partial"])
    metric_cols[2].metric("Missing", summary["missing"])
    metric_cols[3].metric("Blocked", summary["blocked"])

    st.subheader("Claude Code And Terminal")
    st.write(
        "This application is a normal Python terminal CLI. It works inside Claude Code by opening this repo and running the same commands in Claude Code's terminal."
    )
    st.code(
        "pip install -r requirements.txt\n"
        "python -m scripts.init_db --reset --seed\n"
        "python main.py --help\n"
        "python main.py readiness\n"
        "streamlit run app/streamlit_app.py",
        language="powershell",
    )

    st.subheader("Live Action Guardrails")
    guardrail_rows = [
        {"Check": "DRY_RUN=false", "Status": "configured" if not settings.dry_run else "not enabled"},
        {
            "Check": "REAL_API_CONFIRMATION=I_UNDERSTAND_REAL_API_CALLS",
            "Status": "configured"
            if settings.real_api_confirmation == "I_UNDERSTAND_REAL_API_CALLS"
            else "not enabled",
        },
        {"Check": "Approved cost approval record", "Status": "required per action"},
        {"Check": "Provider API key", "Status": "required per provider"},
        {"Check": "No automatic campaign launch", "Status": "enforced by current app boundary"},
    ]
    render_dataframe(pd.DataFrame(guardrail_rows), "Required Before Real Provider Actions")

    df = _readiness_df()
    selected_status = st.selectbox("Filter by status", _status_filter_options(df))
    if selected_status != "All":
        df = df[df["Status"] == selected_status]

    display_df = df.copy()
    if not display_df.empty:
        display_df["Status"] = display_df["Status"].map(status_label)
    st.subheader("SOP Feature Checklist")
    if display_df.empty:
        st.caption("No matching readiness items.")
    else:
        st.write(display_df.to_html(escape=False, index=False), unsafe_allow_html=True)

