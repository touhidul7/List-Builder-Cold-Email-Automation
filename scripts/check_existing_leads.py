"""Local SQLite existing-lead checks before paid sourcing."""

from pydantic import BaseModel, Field

from scripts.db import get_connection


class ExistingLeadSummary(BaseModel):
    """Summary of locally stored leads matching a mandate profile."""

    mandate_id: str | None = None
    industry: str
    geography: str
    matching_companies: int
    companies_with_email: int
    verified_contacts: int
    previously_contacted: int
    usable_existing_leads: int
    recommendation: str
    matched_company_examples: list[str] = Field(default_factory=list)


def _recommendation(matching_companies: int, usable_existing_leads: int) -> str:
    """Return the next local-first sourcing recommendation."""
    if usable_existing_leads >= 10:
        return "Use existing local records first before running paid sources."
    if matching_companies > 0:
        return "Some existing records found, but paid sourcing may still be needed."
    return "No existing records found. Source planning can proceed to low-cost test scrape."


def check_existing_leads(
    industry: str,
    geography: str,
    mandate_id: str | None = None,
    limit_examples: int = 5,
) -> ExistingLeadSummary:
    """Summarize matching local companies and usable contacts."""
    industry_keyword = industry.strip().lower()
    geography_keyword = geography.strip().lower()
    if limit_examples < 0:
        raise ValueError("Example limit cannot be negative.")

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                companies.id AS company_id,
                companies.company_name,
                companies.city,
                companies.province,
                contacts.id AS contact_id,
                contacts.email,
                contacts.email_status,
                contacts.previously_contacted
            FROM companies
            LEFT JOIN contacts ON contacts.company_id = companies.id
            WHERE (
                lower(COALESCE(companies.industry, '')) LIKE ?
                OR lower(companies.company_name) LIKE ?
            )
            AND (
                lower(COALESCE(companies.province, '')) LIKE ?
                OR lower(COALESCE(companies.city, '')) LIKE ?
                OR lower(COALESCE(companies.country, '')) LIKE ?
            )
            ORDER BY companies.company_name, contacts.id
            """,
            (
                f"%{industry_keyword}%",
                f"%{industry_keyword}%",
                f"%{geography_keyword}%",
                f"%{geography_keyword}%",
                f"%{geography_keyword}%",
            ),
        ).fetchall()

    company_ids = {row["company_id"] for row in rows}
    companies_with_email = {
        row["company_id"] for row in rows if row["email"] and row["email"].strip()
    }
    verified_contacts = {
        row["contact_id"]
        for row in rows
        if row["contact_id"] and row["email_status"] == "valid"
    }
    previously_contacted = {
        row["contact_id"]
        for row in rows
        if row["contact_id"] and row["previously_contacted"] == 1
    }
    usable_existing_leads = {
        row["contact_id"]
        for row in rows
        if row["contact_id"]
        and row["email_status"] == "valid"
        and row["previously_contacted"] != 1
    }

    examples: list[str] = []
    seen_examples: set[str] = set()
    for row in rows:
        location = ", ".join(
            value for value in (row["city"], row["province"]) if value
        )
        example = f"{row['company_name']} ({location})" if location else row["company_name"]
        if example not in seen_examples:
            seen_examples.add(example)
            examples.append(example)
        if len(examples) >= limit_examples:
            break

    return ExistingLeadSummary(
        mandate_id=mandate_id,
        industry=industry,
        geography=geography,
        matching_companies=len(company_ids),
        companies_with_email=len(companies_with_email),
        verified_contacts=len(verified_contacts),
        previously_contacted=len(previously_contacted),
        usable_existing_leads=len(usable_existing_leads),
        recommendation=_recommendation(len(company_ids), len(usable_existing_leads)),
        matched_company_examples=examples,
    )
