"""Small Streamlit UI helpers shared by dashboard pages."""

from collections.abc import Mapping

import pandas as pd
import streamlit as st


def apply_app_style() -> None:
    """Apply a compact professional theme over Streamlit defaults."""
    st.markdown(
        """
        <style>
        :root {
            --lb-ink: #17202a;
            --lb-muted: #5f6b7a;
            --lb-border: #d9e1ea;
            --lb-surface: #f7f9fb;
            --lb-good: #0f7b4f;
            --lb-warn: #9a5b00;
            --lb-bad: #b42318;
            --lb-info: #2457a6;
        }
        .block-container {
            padding-top: 1.25rem;
            padding-bottom: 2rem;
            max-width: 1320px;
        }
        [data-testid="stSidebar"] {
            border-right: 1px solid var(--lb-border);
        }
        h1, h2, h3 {
            color: var(--lb-ink);
            letter-spacing: 0;
        }
        h1 {
            font-size: 1.75rem;
            margin-bottom: .25rem;
        }
        h2 {
            font-size: 1.2rem;
            margin-top: 1.25rem;
        }
        h3 {
            font-size: 1rem;
        }
        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid var(--lb-border);
            border-radius: 8px;
            padding: .65rem .8rem;
        }
        div[data-testid="stMetricLabel"] {
            color: var(--lb-muted);
            font-size: .78rem;
        }
        .lb-page-note {
            color: var(--lb-muted);
            font-size: .92rem;
            margin-bottom: .85rem;
        }
        .lb-status {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: .18rem .52rem;
            font-weight: 700;
            font-size: .78rem;
            border: 1px solid transparent;
            white-space: nowrap;
        }
        .lb-status-done, .lb-status-approved, .lb-status-valid {
            color: var(--lb-good);
            background: #eaf7f0;
            border-color: #b9e5cc;
        }
        .lb-status-partial, .lb-status-pending, .lb-status-approval_required {
            color: var(--lb-warn);
            background: #fff5df;
            border-color: #f6d68c;
        }
        .lb-status-missing, .lb-status-rejected, .lb-status-invalid {
            color: var(--lb-bad);
            background: #fff0ed;
            border-color: #ffc9c0;
        }
        .lb-status-blocked, .lb-status-unknown {
            color: #5d3b91;
            background: #f1ebff;
            border-color: #d8c8ff;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_intro(text: str) -> None:
    """Render short page guidance without taking over the interface."""
    st.markdown(f"<div class='lb-page-note'>{text}</div>", unsafe_allow_html=True)


def status_label(status: str) -> str:
    """Return an HTML badge string for DataFrame-independent status displays."""
    normalized = (status or "unknown").lower()
    return f"<span class='lb-status lb-status-{normalized}'>{status or 'unknown'}</span>"


def render_status_badge(status: str) -> None:
    """Render a simple status badge using native Markdown."""
    st.markdown(status_label(status), unsafe_allow_html=True)


def render_metric_row(counts: Mapping[str, int]) -> None:
    """Render core database counts in a dense metric grid."""
    keys = (
        "mandates",
        "companies",
        "contacts",
        "source_runs",
        "lead_scores",
        "personalization",
        "email_sequences",
        "campaigns",
        "campaign_leads",
    )
    for index in range(0, len(keys), 3):
        columns = st.columns(3)
        for column, key in zip(columns, keys[index : index + 3]):
            column.metric(key.replace("_", " ").title(), counts.get(key, 0))


def show_dry_run_banner() -> None:
    """Show the global dry-run warning."""
    st.info("Dry-run mode: no external APIs are called and no emails or campaigns are sent.")


def show_db_missing_warning() -> None:
    """Show the local database setup command."""
    st.warning("Local database not found. Run: `python -m scripts.init_db --reset --seed`")


def render_dataframe(df: pd.DataFrame, title: str) -> None:
    """Render a titled DataFrame with an empty-state message."""
    st.subheader(title)
    if df.empty:
        st.caption("No records yet.")
        return
    st.dataframe(df, use_container_width=True, hide_index=True)


def success_box(message: str) -> None:
    """Render a success message."""
    st.success(message)


def warning_box(message: str) -> None:
    """Render a warning message."""
    st.warning(message)


def error_box(message: str) -> None:
    """Render an error message."""
    st.error(message)
