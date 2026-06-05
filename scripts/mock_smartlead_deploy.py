"""DRY_RUN-only paused Smartlead campaign deployment simulation."""

import uuid

from pydantic import BaseModel

from scripts.cold_email_copywriting import save_email_sequence_for_mandate
from scripts.config import get_settings
from scripts.db import get_connection


class MockSmartleadLead(BaseModel):
    """One approved local contact shaped for a future Smartlead upload."""

    contact_id: str
    company_id: str
    email: str
    full_name: str | None = None
    company_name: str
    opening_line: str | None = None
    fit_rationale: str | None = None
    suggested_cta: str | None = None
    upload_status: str = "ready"


class MockSmartleadCampaignResult(BaseModel):
    """Summary of a local-only paused campaign deployment simulation."""

    campaign_id: str
    smartlead_campaign_id: str
    campaign_name: str
    campaign_status: str
    leads_selected: int
    leads_uploaded: int
    sequence_attached: bool
    status: str


def _short_uuid() -> str:
    return uuid.uuid4().hex[:12]


def get_approved_contacts_for_campaign(
    mandate_id: str,
    limit: int = 100,
) -> list[MockSmartleadLead]:
    """Return valid, uncontacted contacts ordered by Tier 1 then Tier 2 fit."""
    if limit < 0:
        raise ValueError("Campaign lead limit cannot be negative.")
    if limit == 0:
        return []

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                contacts.id AS contact_id,
                contacts.company_id,
                contacts.email,
                contacts.full_name,
                companies.company_name,
                companies.priority_tier,
                companies.fit_score,
                personalization.opening_line,
                personalization.fit_rationale,
                personalization.suggested_cta
            FROM contacts
            JOIN companies ON companies.id = contacts.company_id
            LEFT JOIN personalization ON personalization.contact_id = contacts.id
            WHERE companies.mandate_id = ?
              AND contacts.email_status = 'valid'
              AND COALESCE(contacts.previously_contacted, 0) = 0
              AND contacts.email IS NOT NULL
              AND trim(contacts.email) != ''
              AND companies.priority_tier IN ('Tier 1', 'Tier 2')
            ORDER BY
                CASE companies.priority_tier WHEN 'Tier 1' THEN 0 ELSE 1 END,
                COALESCE(companies.fit_score, 0) DESC,
                companies.company_name,
                contacts.email
            LIMIT ?
            """,
            (mandate_id, limit),
        ).fetchall()

    return [
        MockSmartleadLead(
            contact_id=str(row["contact_id"]),
            company_id=str(row["company_id"]),
            email=str(row["email"]),
            full_name=row["full_name"],
            company_name=str(row["company_name"]),
            opening_line=row["opening_line"],
            fit_rationale=row["fit_rationale"],
            suggested_cta=row["suggested_cta"],
        )
        for row in rows
    ]


def _latest_campaign(connection: object, mandate_id: str) -> dict | None:
    row = connection.execute(
        """
        SELECT *
        FROM campaigns
        WHERE mandate_id = ?
        ORDER BY created_at DESC, rowid DESC
        LIMIT 1
        """,
        (mandate_id,),
    ).fetchone()
    return dict(row) if row is not None else None


def create_mock_smartlead_campaign(
    mandate_id: str,
    limit: int = 100,
) -> MockSmartleadCampaignResult:
    """Create/update a paused local campaign and mock-upload approved leads."""
    if not get_settings().dry_run:
        raise PermissionError("Mock Smartlead deployment requires DRY_RUN=true.")
    if limit < 0:
        raise ValueError("Campaign lead limit cannot be negative.")

    with get_connection() as connection:
        mandate = connection.execute(
            "SELECT * FROM mandates WHERE id = ?",
            (mandate_id,),
        ).fetchone()
        if mandate is None:
            raise ValueError(f"Mandate not found: {mandate_id}")

        campaign = _latest_campaign(connection, mandate_id)
        if campaign is None:
            campaign_id = str(uuid.uuid4())
            campaign_name = f"{mandate['mandate_name']} - Mock Smartlead"
            connection.execute(
                """
                INSERT INTO campaigns (id, mandate_id, campaign_name, campaign_status)
                VALUES (?, ?, ?, 'paused')
                """,
                (campaign_id, mandate_id, campaign_name),
            )
            connection.commit()
        else:
            campaign_id = str(campaign["id"])
            campaign_name = str(campaign["campaign_name"])

    with get_connection() as connection:
        sequence = connection.execute(
            "SELECT 1 FROM email_sequences WHERE campaign_id = ? LIMIT 1",
            (campaign_id,),
        ).fetchone()
    if sequence is None:
        save_email_sequence_for_mandate(mandate_id)

    leads = get_approved_contacts_for_campaign(mandate_id, limit)
    uploaded = 0
    with get_connection() as connection:
        smartlead_campaign_id = connection.execute(
            "SELECT smartlead_campaign_id FROM campaigns WHERE id = ?",
            (campaign_id,),
        ).fetchone()["smartlead_campaign_id"]
        if not smartlead_campaign_id:
            smartlead_campaign_id = f"mock_sl_campaign_{_short_uuid()}"

        for lead in leads:
            exists = connection.execute(
                """
                SELECT 1
                FROM campaign_leads
                WHERE campaign_id = ? AND contact_id = ?
                LIMIT 1
                """,
                (campaign_id, lead.contact_id),
            ).fetchone()
            if exists is not None:
                continue
            connection.execute(
                """
                INSERT INTO campaign_leads (
                    id,
                    campaign_id,
                    contact_id,
                    smartlead_lead_id,
                    upload_status,
                    approval_status
                ) VALUES (?, ?, ?, ?, 'uploaded_mock', 'approved')
                """,
                (
                    str(uuid.uuid4()),
                    campaign_id,
                    lead.contact_id,
                    f"mock_sl_lead_{_short_uuid()}",
                ),
            )
            uploaded += 1

        connection.execute(
            """
            UPDATE campaigns
            SET
                smartlead_campaign_id = ?,
                campaign_status = 'paused',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (smartlead_campaign_id, campaign_id),
        )
        sequence_attached = (
            connection.execute(
                "SELECT 1 FROM email_sequences WHERE campaign_id = ? LIMIT 1",
                (campaign_id,),
            ).fetchone()
            is not None
        )
        campaign = connection.execute(
            "SELECT * FROM campaigns WHERE id = ?",
            (campaign_id,),
        ).fetchone()
        connection.commit()

    return MockSmartleadCampaignResult(
        campaign_id=campaign_id,
        smartlead_campaign_id=str(smartlead_campaign_id),
        campaign_name=str(campaign["campaign_name"]),
        campaign_status=str(campaign["campaign_status"]),
        leads_selected=len(leads),
        leads_uploaded=uploaded,
        sequence_attached=sequence_attached,
        status="uploaded_mock_paused",
    )
