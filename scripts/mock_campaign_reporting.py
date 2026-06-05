"""DRY_RUN-only mock campaign event reporting."""

import uuid

from pydantic import BaseModel

from scripts.config import get_settings
from scripts.db import get_connection


class CampaignEventSummary(BaseModel):
    """Counts for synthetic outreach events stored in local SQLite."""

    campaign_id: str
    sent: int
    opened: int
    replied: int
    bounced: int
    interested: int
    not_interested: int
    meeting_booked: int


def _insert_event(
    connection: object,
    campaign_id: str,
    contact_id: str,
    event_type: str,
) -> None:
    connection.execute(
        """
        INSERT INTO outreach_events (id, contact_id, campaign_id, event_type, notes)
        VALUES (?, ?, ?, ?, 'Synthetic dry-run event. No real email was sent.')
        """,
        (str(uuid.uuid4()), contact_id, campaign_id, event_type),
    )


def generate_mock_campaign_events(campaign_id: str) -> CampaignEventSummary:
    """Generate deterministic mock reporting events for uploaded campaign leads."""
    if not get_settings().dry_run:
        raise PermissionError("Mock campaign reporting requires DRY_RUN=true.")

    counts = {
        "sent": 0,
        "opened": 0,
        "replied": 0,
        "bounced": 0,
        "interested": 0,
        "not_interested": 0,
        "meeting_booked": 0,
    }
    with get_connection() as connection:
        leads = connection.execute(
            """
            SELECT campaign_leads.*, contacts.id AS contact_id
            FROM campaign_leads
            JOIN contacts ON contacts.id = campaign_leads.contact_id
            WHERE campaign_leads.campaign_id = ?
            ORDER BY campaign_leads.created_at, campaign_leads.id
            """,
            (campaign_id,),
        ).fetchall()
        for index, lead in enumerate(leads, start=1):
            contact_id = str(lead["contact_id"])
            _insert_event(connection, campaign_id, contact_id, "sent_mock")
            counts["sent"] += 1
            if index % 2 == 0:
                _insert_event(connection, campaign_id, contact_id, "opened_mock")
                counts["opened"] += 1
            if index % 5 == 0:
                _insert_event(connection, campaign_id, contact_id, "replied_mock")
                counts["replied"] += 1
            if index % 10 == 0:
                _insert_event(connection, campaign_id, contact_id, "interested_mock")
                counts["interested"] += 1
            if index % 15 == 0:
                _insert_event(connection, campaign_id, contact_id, "meeting_booked_mock")
                counts["meeting_booked"] += 1
            if index % 12 == 0:
                _insert_event(connection, campaign_id, contact_id, "not_interested_mock")
                counts["not_interested"] += 1
        connection.commit()

    return CampaignEventSummary(campaign_id=campaign_id, **counts)
