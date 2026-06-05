"""Real Smartlead draft campaign creation behind explicit safety gates.

This module creates draft campaigns only. It does not add senders, start
campaigns, or send emails.
"""

import uuid

from pydantic import BaseModel
import requests

from scripts.config import get_settings
from scripts.db import get_connection
from scripts.real_safety import require_real_api_enabled


SMARTLEAD_CREATE_CAMPAIGN_URL = "https://server.smartlead.ai/api/v1/campaigns/create"


class SmartleadDraftCampaignRequest(BaseModel):
    """Approved Smartlead draft campaign creation input."""

    mandate_id: str
    approval_id: str
    campaign_name: str | None = None


class SmartleadDraftCampaignResult(BaseModel):
    """Local and external IDs for a created Smartlead draft campaign."""

    campaign_id: str
    smartlead_campaign_id: str
    campaign_name: str
    campaign_status: str


def _mandate_name(mandate_id: str) -> str:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT mandate_name FROM mandates WHERE id = ?",
            (mandate_id,),
        ).fetchone()
    if row is None:
        raise ValueError(f"Mandate not found: {mandate_id}")
    return str(row["mandate_name"])


def create_smartlead_draft_campaign_real(
    request: SmartleadDraftCampaignRequest,
    timeout: int = 30,
) -> SmartleadDraftCampaignResult:
    """Create a Smartlead campaign in its default drafted state."""
    settings = get_settings()
    require_real_api_enabled("Smartlead", settings.smartlead_api_key, request.approval_id)
    campaign_name = request.campaign_name or f"{_mandate_name(request.mandate_id)} - Real Draft"
    response = requests.post(
        SMARTLEAD_CREATE_CAMPAIGN_URL,
        params={"api_key": settings.smartlead_api_key},
        json={"name": campaign_name},
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    smartlead_campaign_id = str(data["id"])
    campaign_id = str(uuid.uuid4())
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO campaigns (
                id,
                mandate_id,
                smartlead_campaign_id,
                campaign_name,
                campaign_status
            ) VALUES (?, ?, ?, ?, 'drafted_external')
            """,
            (
                campaign_id,
                request.mandate_id,
                smartlead_campaign_id,
                campaign_name,
            ),
        )
        connection.commit()
    return SmartleadDraftCampaignResult(
        campaign_id=campaign_id,
        smartlead_campaign_id=smartlead_campaign_id,
        campaign_name=campaign_name,
        campaign_status="drafted_external",
    )
