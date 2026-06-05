"""Read helpers for the Streamlit dashboard.

These helpers keep Streamlit pages thin and avoid mutating local SQLite state.
"""

from pathlib import Path
from typing import Any

import pandas as pd

from scripts import db


COUNT_TABLES = (
    "mandates",
    "companies",
    "contacts",
    "cost_approvals",
    "source_runs",
    "lead_scores",
    "research_logs",
    "personalization",
    "email_sequences",
    "campaigns",
    "campaign_leads",
    "outreach_events",
    "domains",
    "inboxes",
)


def get_connection() -> Any:
    """Open the local SQLite database via the backend helper."""
    return db.get_connection()


def fetch_table(query: str, params: tuple = ()) -> pd.DataFrame:
    """Execute a read-only query and return a DataFrame."""
    normalized = query.strip().lower()
    if not (normalized.startswith("select") or normalized.startswith("with")):
        raise ValueError("fetch_table only accepts read-only SELECT queries.")
    with get_connection() as connection:
        return pd.read_sql_query(query, connection, params=params)


def get_db_counts() -> dict[str, int]:
    """Return local SQLite row counts for dashboard metrics."""
    if not ensure_local_db_exists():
        return {table_name: 0 for table_name in COUNT_TABLES}
    with get_connection() as connection:
        return {
            table_name: db.count_rows(connection, table_name)
            for table_name in COUNT_TABLES
        }


def get_latest_mandate_id() -> str | None:
    """Return the newest active mandate ID, if present."""
    if not ensure_local_db_exists():
        return None
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id
            FROM mandates
            WHERE status = 'active'
            ORDER BY created_at DESC, rowid DESC
            LIMIT 1
            """
        ).fetchone()
    return str(row["id"]) if row else None


def get_mandates_df() -> pd.DataFrame:
    """Return stored mandates ordered newest first."""
    return fetch_table(
        """
        SELECT *
        FROM mandates
        ORDER BY created_at DESC, rowid DESC
        """
    )


def get_source_runs_df(mandate_id: str | None = None) -> pd.DataFrame:
    """Return source runs, optionally filtered by mandate."""
    query = "SELECT * FROM source_runs"
    params: tuple[str, ...] = ()
    if mandate_id:
        query += " WHERE mandate_id = ?"
        params = (mandate_id,)
    query += " ORDER BY created_at DESC, rowid DESC"
    return fetch_table(query, params)


def get_companies_df(mandate_id: str | None = None) -> pd.DataFrame:
    """Return companies, optionally filtered by mandate."""
    query = "SELECT * FROM companies"
    params: tuple[str, ...] = ()
    if mandate_id:
        query += " WHERE mandate_id = ?"
        params = (mandate_id,)
    query += " ORDER BY created_at DESC, rowid DESC"
    return fetch_table(query, params)


def get_contacts_df(mandate_id: str | None = None) -> pd.DataFrame:
    """Return contacts joined to company names, optionally filtered by mandate."""
    query = """
        SELECT
            contacts.*,
            companies.company_name,
            companies.mandate_id
        FROM contacts
        LEFT JOIN companies ON companies.id = contacts.company_id
    """
    params: tuple[str, ...] = ()
    if mandate_id:
        query += " WHERE companies.mandate_id = ?"
        params = (mandate_id,)
    query += " ORDER BY contacts.created_at DESC, contacts.rowid DESC"
    return fetch_table(query, params)


def get_campaigns_df() -> pd.DataFrame:
    """Return campaigns ordered newest first."""
    return fetch_table(
        """
        SELECT *
        FROM campaigns
        ORDER BY created_at DESC, rowid DESC
        """
    )


def short_id(value: str | None, length: int = 8) -> str:
    """Return a compact ID for display tables."""
    if not value:
        return "-"
    return str(value)[:length]


def ensure_local_db_exists() -> bool:
    """Return whether the configured local SQLite file exists."""
    return Path(db.get_local_db_path()).exists()
