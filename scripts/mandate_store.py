"""Local SQLite persistence for parsed mandates."""

import json
import uuid

from scripts.config import get_settings
from scripts.db import get_connection
from scripts.mandate_intake import Mandate


def save_mandate(mandate: Mandate) -> str:
    """Insert a parsed mandate into local SQLite and return its generated ID."""
    mandate_id = str(uuid.uuid4())
    settings = get_settings()
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO mandates (
                id,
                mandate_name,
                mandate_type,
                industry,
                geography,
                target_lead_count,
                campaign_goal,
                company_size,
                target_titles,
                exclusions,
                budget_cap,
                amount_spent,
                status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'active')
            """,
            (
                mandate_id,
                mandate.mandate_name,
                mandate.mandate_type,
                mandate.industry,
                mandate.geography,
                mandate.target_lead_count,
                mandate.campaign_goal,
                mandate.company_size,
                json.dumps(mandate.target_titles),
                json.dumps(mandate.exclusions),
                settings.default_budget_cap,
            ),
        )
        connection.commit()
    return mandate_id


def get_mandate(mandate_id: str) -> dict | None:
    """Fetch one locally stored mandate."""
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM mandates WHERE id = ?",
            (mandate_id,),
        ).fetchone()
    return dict(row) if row is not None else None


def list_mandates(limit: int = 10) -> list[dict]:
    """Return recently created local mandates."""
    if limit < 1:
        raise ValueError("Mandate list limit must be positive.")
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM mandates
            ORDER BY created_at DESC, rowid DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
