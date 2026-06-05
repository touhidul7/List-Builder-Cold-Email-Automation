"""DRY_RUN-only cold email strategy and copy generation."""

import uuid

from pydantic import BaseModel

from scripts.config import get_settings
from scripts.db import get_connection
from scripts.mandate_store import get_mandate


class ColdEmailStrategy(BaseModel):
    """Reviewable campaign strategy generated from one local mandate."""

    mandate_id: str
    campaign_name: str
    audience: str
    campaign_goal: str
    offer_angle: str
    primary_cta: str
    objections: list[str]
    compliance_notes: list[str]


class ColdEmailSequence(BaseModel):
    """Short plain-text email sequence with merge placeholders."""

    campaign_name: str
    subject_a: str
    subject_b: str
    email_1: str
    email_2: str
    email_3: str
    email_4: str | None = None
    unsubscribe_line: str
    compliance_notes: str


def build_cold_email_strategy(mandate: dict) -> ColdEmailStrategy:
    """Create a safe, local-only campaign strategy from stored mandate data."""
    mandate_type = str(mandate.get("mandate_type") or "").lower()
    mandate_name = str(mandate.get("mandate_name") or "Local Outreach")
    common_notes = [
        "Include a clear opt-out line.",
        "Keep message accurate and non-misleading.",
    ]
    if "acquisition" in mandate_type:
        audience = "Business owners/operators in the target industry and geography"
        campaign_goal = str(
            mandate.get("campaign_goal") or "book acquisition conversation"
        )
        offer_angle = (
            "Confidential conversation about potential acquisition interest "
            "from a qualified buyer."
        )
        primary_cta = "Open to a brief confidential conversation next week?"
        objections = [
            "Not interested in selling",
            "Concerned about confidentiality",
            "Too busy to respond",
            "Wants more information before engaging",
        ]
        compliance_notes = [
            "Do not include confidential buyer details before NDA.",
            *common_notes,
        ]
    elif "investor" in mandate_type:
        audience = "Investors relevant to the mandate industry and geography"
        campaign_goal = "book investor conversation"
        offer_angle = (
            "Introduce a relevant investment or acquisition opportunity at a high level."
        )
        primary_cta = "Open to reviewing a short overview?"
        objections = [
            "Not a fit for the current mandate",
            "Needs a concise overview before engaging",
            "Timing is not right",
        ]
        compliance_notes = [
            "Do not include confidential deal details before approval.",
            "Investor campaigns require human approval before launch.",
            *common_notes,
        ]
    else:
        audience = "Relevant business contacts in the target industry and geography"
        campaign_goal = str(mandate.get("campaign_goal") or "book intro call")
        offer_angle = "Introductory conversation based on relevant business fit."
        primary_cta = "Open to a brief introductory call next week?"
        objections = [
            "Not a current priority",
            "Needs more context before engaging",
            "Too busy to respond",
        ]
        compliance_notes = common_notes

    return ColdEmailStrategy(
        mandate_id=str(mandate["id"]),
        campaign_name=f"{mandate_name} - Draft Outreach",
        audience=audience,
        campaign_goal=campaign_goal,
        offer_angle=offer_angle,
        primary_cta=primary_cta,
        objections=objections,
        compliance_notes=compliance_notes,
    )


def generate_mock_email_sequence(strategy: ColdEmailStrategy) -> ColdEmailSequence:
    """Create short, compliant merge-template copy without calling Claude."""
    unsubscribe_line = (
        "If this is not relevant, just reply 'not interested' and I will not follow up."
    )
    return ColdEmailSequence(
        campaign_name=strategy.campaign_name,
        subject_a="Quick question for {{company_name}}",
        subject_b="Brief confidential conversation?",
        email_1=(
            "Hi {{first_name}},\n\n"
            "{{opening_line}}\n\n"
            f"{strategy.offer_angle}\n\n"
            "{{suggested_cta}}\n\n"
            f"{unsubscribe_line}"
        ),
        email_2=(
            "Hi {{first_name}},\n\n"
            "Following up in case my note was missed. "
            "{{fit_rationale}}\n\n"
            "{{suggested_cta}}\n\n"
            f"{unsubscribe_line}"
        ),
        email_3=(
            "Hi {{first_name}},\n\n"
            "I wanted to check in once more. If a brief conversation is not "
            "relevant for {{company_name}}, no problem.\n\n"
            f"{unsubscribe_line}"
        ),
        unsubscribe_line=unsubscribe_line,
        compliance_notes=" ".join(strategy.compliance_notes),
    )


def save_email_sequence_for_mandate(mandate_id: str) -> str:
    """Persist a draft sequence for a local mandate without API calls."""
    if not get_settings().dry_run:
        raise PermissionError("Mock cold email copywriting requires DRY_RUN=true.")
    mandate = get_mandate(mandate_id)
    if mandate is None:
        raise ValueError(f"Mandate not found: {mandate_id}")
    strategy = build_cold_email_strategy(mandate)
    sequence = generate_mock_email_sequence(strategy)

    with get_connection() as connection:
        campaign = connection.execute(
            """
            SELECT *
            FROM campaigns
            WHERE mandate_id = ?
            ORDER BY created_at DESC, rowid DESC
            LIMIT 1
            """,
            (mandate_id,),
        ).fetchone()
        if campaign is None:
            campaign_id = str(uuid.uuid4())
            connection.execute(
                """
                INSERT INTO campaigns (id, mandate_id, campaign_name, campaign_status)
                VALUES (?, ?, ?, 'draft')
                """,
                (campaign_id, mandate_id, strategy.campaign_name),
            )
        else:
            campaign_id = str(campaign["id"])

        sequence_id = str(uuid.uuid4())
        connection.execute(
            """
            INSERT INTO email_sequences (
                id,
                campaign_id,
                sequence_name,
                subject_a,
                subject_b,
                email_1,
                email_2,
                email_3,
                email_4,
                unsubscribe_line,
                compliance_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sequence_id,
                campaign_id,
                sequence.campaign_name,
                sequence.subject_a,
                sequence.subject_b,
                sequence.email_1,
                sequence.email_2,
                sequence.email_3,
                sequence.email_4,
                sequence.unsubscribe_line,
                sequence.compliance_notes,
            ),
        )
        connection.commit()
    return sequence_id


def get_latest_email_sequence(mandate_id: str) -> dict | None:
    """Return the newest locally saved sequence for one mandate."""
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                email_sequences.*,
                campaigns.campaign_name,
                campaigns.mandate_id
            FROM email_sequences
            JOIN campaigns ON campaigns.id = email_sequences.campaign_id
            WHERE campaigns.mandate_id = ?
            ORDER BY email_sequences.created_at DESC, email_sequences.rowid DESC
            LIMIT 1
            """,
            (mandate_id,),
        ).fetchone()
    return dict(row) if row is not None else None
