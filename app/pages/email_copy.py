"""Mock cold email copy page."""

import streamlit as st

from app.ui_helpers import render_dataframe, show_dry_run_banner, success_box, warning_box
from app.utils import fetch_table, get_mandates_df
from scripts.cold_email_copywriting import get_latest_email_sequence, save_email_sequence_for_mandate


def render() -> None:
    """Render mock sequence generation and saved email sequences."""
    st.title("Email Copy")
    show_dry_run_banner()
    st.caption("Copy is generated locally for review and uses merge placeholders; it does not call Claude.")
    mandates = get_mandates_df()
    if mandates.empty:
        warning_box("No mandates found.")
        return
    mandate_id = st.selectbox("Mandate", mandates["id"].tolist())
    if st.button("Generate Email Copy Mock"):
        sequence_id = save_email_sequence_for_mandate(mandate_id)
        success_box(f"Saved mock email sequence: {sequence_id}")

    latest = get_latest_email_sequence(mandate_id)
    if latest:
        st.subheader("Latest Email Sequence")
        st.write(f"Campaign name: {latest['campaign_name']}")
        st.write(f"Subject A: {latest['subject_a']}")
        st.write(f"Subject B: {latest['subject_b']}")
        for field in ("email_1", "email_2", "email_3", "email_4"):
            if latest[field]:
                st.text_area(field.replace("_", " ").title(), latest[field], height=130)
        st.write(f"Unsubscribe line: {latest['unsubscribe_line']}")
        st.write(f"Compliance notes: {latest['compliance_notes']}")

    sequences = fetch_table(
        """
        SELECT
            email_sequences.id,
            campaigns.campaign_name,
            email_sequences.subject_a,
            email_sequences.subject_b,
            email_sequences.created_at
        FROM email_sequences
        JOIN campaigns ON campaigns.id = email_sequences.campaign_id
        WHERE campaigns.mandate_id = ?
        ORDER BY email_sequences.created_at DESC, email_sequences.rowid DESC
        """,
        (mandate_id,),
    )
    render_dataframe(sequences, "Saved Email Sequences")
