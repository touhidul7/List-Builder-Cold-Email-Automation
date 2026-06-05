"""Real data CSV import page."""

import pandas as pd
import streamlit as st

from app.ui_helpers import render_dataframe, show_dry_run_banner, success_box, warning_box
from app.utils import get_mandates_df
from scripts.import_real_data import import_real_lead_rows


REQUIRED_COLUMNS = ("company_name",)
HELP_COLUMNS = (
    "company_name",
    "website",
    "industry",
    "city",
    "province",
    "country",
    "phone",
    "source",
    "source_url",
    "full_name",
    "title",
    "email",
    "email_status",
    "previously_contacted",
)


def _clean_records(df: pd.DataFrame) -> list[dict]:
    """Convert uploaded DataFrame to importer records."""
    normalized = df.rename(columns={column: column.strip().lower() for column in df.columns})
    return normalized.where(pd.notnull(normalized), None).to_dict(orient="records")


def render() -> None:
    """Render real data upload/import workflow."""
    st.title("Real Data Import")
    show_dry_run_banner()
    st.info(
        "Use this page for real lead lists you already have. It stores records in local SQLite only; "
        "it does not enrich, verify, email, or call provider APIs."
    )

    mandates = get_mandates_df()
    if mandates.empty:
        warning_box("Create a mandate before importing real data.")
        return

    mandate_id = st.selectbox("Import into mandate", mandates["id"].tolist())
    with st.expander("CSV columns"):
        st.write("Minimum required column: `company_name`")
        st.write("Recommended columns:")
        st.code(",".join(HELP_COLUMNS), language="text")
        st.caption("Set `email_status` to `valid` only when you have already verified the email.")

    uploaded = st.file_uploader("Upload real leads CSV", type=["csv"])
    if uploaded is None:
        return

    df = pd.read_csv(uploaded)
    normalized_columns = {column.strip().lower() for column in df.columns}
    missing = [column for column in REQUIRED_COLUMNS if column not in normalized_columns]
    if missing:
        warning_box(f"Missing required columns: {', '.join(missing)}")
        return

    render_dataframe(df.head(25), "Preview First 25 Rows")
    st.caption(f"Rows detected: {len(df)}")
    confirmed = st.checkbox(
        "I confirm this data is permitted for business outreach and should be stored locally."
    )
    if st.button("Import Real Data"):
        if not confirmed:
            warning_box("Confirm permission before importing real data.")
            return
        summary = import_real_lead_rows(mandate_id, _clean_records(df))
        success_box("Real data import completed.")
        st.json(summary.model_dump())
