"""End-to-end DRY_RUN pipeline orchestration using local SQLite only."""

from pydantic import BaseModel

from scripts.check_existing_leads import check_existing_leads
from scripts.cold_email_copywriting import save_email_sequence_for_mandate
from scripts.db import get_connection
from scripts.init_db import initialize_database
from scripts.mandate_intake import parse_mandate
from scripts.mandate_store import save_mandate
from scripts.mock_email_enrichment import enrich_companies_without_contacts
from scripts.mock_email_verification import verify_contacts_mock
from scripts.mock_smartlead_deploy import create_mock_smartlead_campaign
from scripts.research_best_leads import research_tier_one_leads
from scripts.run_apify_google_maps import run_apify_google_maps_mock
from scripts.score_leads import score_companies_for_mandate
from scripts.source_run_planner import create_source_runs_for_mandate


class DryPipelineSummary(BaseModel):
    """Summary of one full local mock SOP run."""

    mandate_id: str
    companies_imported: int
    contacts_created: int
    valid_emails: int
    leads_scored: int
    tier_1_leads: int
    personalization_records: int
    campaign_id: str
    smartlead_campaign_id: str
    campaign_status: str
    campaign_leads_uploaded: int
    note: str = "No external APIs were called."


def _find_google_maps_run(mandate_id: str) -> dict:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM source_runs
            WHERE mandate_id = ?
              AND lower(provider || ' ' || source_type) LIKE '%apify%'
              AND lower(provider || ' ' || source_type) LIKE '%maps%'
            ORDER BY created_at DESC, rowid DESC
            LIMIT 1
            """,
            (mandate_id,),
        ).fetchone()
    if row is None:
        raise ValueError("No Apify Google Maps source run was planned.")
    return dict(row)


def _count_for_mandate(table_name: str, mandate_id: str) -> int:
    with get_connection() as connection:
        if table_name == "contacts":
            row = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM contacts
                JOIN companies ON companies.id = contacts.company_id
                WHERE companies.mandate_id = ?
                """,
                (mandate_id,),
            ).fetchone()
        elif table_name == "valid_emails":
            row = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM contacts
                JOIN companies ON companies.id = contacts.company_id
                WHERE companies.mandate_id = ? AND contacts.email_status = 'valid'
                """,
                (mandate_id,),
            ).fetchone()
        elif table_name == "tier_1":
            row = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM companies
                WHERE mandate_id = ? AND priority_tier = 'Tier 1'
                """,
                (mandate_id,),
            ).fetchone()
        elif table_name == "personalization":
            row = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM personalization
                JOIN contacts ON contacts.id = personalization.contact_id
                JOIN companies ON companies.id = contacts.company_id
                WHERE companies.mandate_id = ?
                """,
                (mandate_id,),
            ).fetchone()
        else:
            row = connection.execute(
                f"SELECT COUNT(*) AS count FROM {table_name} WHERE mandate_id = ?",
                (mandate_id,),
            ).fetchone()
    return int(row["count"])


def run_dry_pipeline(
    raw_prompt: str,
    limit: int = 25,
    reset_db: bool = False,
) -> DryPipelineSummary:
    """Run the full mock SOP workflow without manual IDs or external calls."""
    if limit < 0:
        raise ValueError("Dry pipeline limit cannot be negative.")
    if reset_db:
        initialize_database(reset=True, seed=True)

    mandate = parse_mandate(raw_prompt)
    mandate_id = save_mandate(mandate)
    check_existing_leads(mandate.industry, mandate.geography, mandate_id=mandate_id)
    create_source_runs_for_mandate(mandate_id)
    source_run = _find_google_maps_run(mandate_id)
    maps_summary = run_apify_google_maps_mock(
        mandate_id,
        source_run["id"],
        source_run["query"],
        limit=limit,
    )
    contacts = enrich_companies_without_contacts(mandate_id=mandate_id, limit=limit)
    verify_contacts_mock(mandate_id=mandate_id, limit=max(limit, 100))
    scored = score_companies_for_mandate(mandate_id)
    research_tier_one_leads(mandate_id=mandate_id, limit=limit)
    save_email_sequence_for_mandate(mandate_id)
    campaign = create_mock_smartlead_campaign(mandate_id, limit=limit)

    return DryPipelineSummary(
        mandate_id=mandate_id,
        companies_imported=int(maps_summary["records_imported"]),
        contacts_created=len(contacts),
        valid_emails=_count_for_mandate("valid_emails", mandate_id),
        leads_scored=len(scored),
        tier_1_leads=_count_for_mandate("tier_1", mandate_id),
        personalization_records=_count_for_mandate("personalization", mandate_id),
        campaign_id=campaign.campaign_id,
        smartlead_campaign_id=campaign.smartlead_campaign_id,
        campaign_status=campaign.campaign_status,
        campaign_leads_uploaded=campaign.leads_uploaded,
    )
