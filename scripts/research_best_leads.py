"""DRY_RUN-only Tier 1 research and personalization from local SQLite fields."""

import json
import uuid

from pydantic import BaseModel, Field

from scripts.config import get_settings
from scripts.db import get_connection


class ResearchResult(BaseModel):
    """Safe personalization generated only from available local fields."""

    company_id: str
    contact_id: str | None = None
    company_name: str
    contact_name: str | None = None
    priority_tier: str
    fit_score: int
    opening_line: str
    fit_rationale: str
    outreach_angle: str
    suggested_cta: str
    research_notes: str
    source_urls: list[str] = Field(default_factory=list)


def _source_urls(company: dict) -> list[str]:
    """Return unique URLs already stored on the local company record."""
    urls: list[str] = []
    for field in ("website", "source_url"):
        value = company.get(field)
        if value and value not in urls:
            urls.append(str(value))
    return urls


def generate_mock_research(
    company: dict,
    contact: dict | None = None,
) -> ResearchResult:
    """Generate non-fabricated personalization from local database fields."""
    company_name = str(company["company_name"])
    city = str(company.get("city") or "local")
    province = str(company.get("province") or "market")
    industry = str(company.get("industry") or "business")
    mandate_type = str(company.get("mandate_type") or "").lower()
    contact = contact or {}

    if "acquisition" in mandate_type:
        outreach_angle = (
            "Confidential conversation about whether the owner would consider "
            "strategic acquisition interest."
        )
    elif "investor" in mandate_type:
        outreach_angle = "Relevant investor outreach based on geography and sector fit."
    else:
        outreach_angle = "Introductory business development outreach."

    notes = [
        f"Local database lists industry as {industry}.",
        f"Local database lists location as {city}, {province}.",
    ]
    if company.get("website"):
        notes.append(f"Website on file: {company['website']}.")
    if company.get("phone"):
        notes.append("Phone number is present in the local database.")
    if contact.get("full_name"):
        title = f" ({contact['title']})" if contact.get("title") else ""
        notes.append(f"Selected contact on file: {contact['full_name']}{title}.")

    return ResearchResult(
        company_id=str(company["id"]),
        contact_id=str(contact["id"]) if contact.get("id") else None,
        company_name=company_name,
        contact_name=str(contact["full_name"]) if contact.get("full_name") else None,
        priority_tier=str(company.get("priority_tier") or "unknown"),
        fit_score=int(company.get("fit_score") or 0),
        opening_line=(
            f"I noticed {company_name} serves the {city}/{province} market "
            "with a clear local presence."
        ),
        fit_rationale=(
            f"{company_name} fits the local research criteria based on its "
            f"{industry} industry record, {city}/{province} geography, and "
            "local operator signals stored in the database."
        ),
        outreach_angle=outreach_angle,
        suggested_cta="Open to a brief confidential conversation next week?",
        research_notes=" ".join(notes),
        source_urls=_source_urls(company),
    )


def _best_contact(connection: object, company_id: str) -> dict | None:
    """Load a valid-email contact first, then any available local contact."""
    row = connection.execute(
        """
        SELECT *
        FROM contacts
        WHERE company_id = ?
        ORDER BY
            CASE WHEN email_status = 'valid' THEN 0 ELSE 1 END,
            CASE WHEN email IS NOT NULL AND trim(email) != '' THEN 0 ELSE 1 END,
            created_at,
            id
        LIMIT 1
        """,
        (company_id,),
    ).fetchone()
    return dict(row) if row is not None else None


def _already_researched(
    connection: object,
    company_id: str,
    contact_id: str | None,
) -> bool:
    """Avoid duplicate personalization for the selected local lead."""
    if contact_id:
        return (
            connection.execute(
                "SELECT 1 FROM personalization WHERE contact_id = ? LIMIT 1",
                (contact_id,),
            ).fetchone()
            is not None
        )
    return (
        connection.execute(
            """
            SELECT 1
            FROM research_logs
            WHERE company_id = ?
              AND contact_id IS NULL
              AND research_type = 'mock_tier_1_research'
            LIMIT 1
            """,
            (company_id,),
        ).fetchone()
        is not None
    )


def research_tier_one_leads(
    mandate_id: str | None = None,
    limit: int = 25,
    include_tier_two: bool = False,
) -> list[ResearchResult]:
    """Persist mock Tier 1 research without browsing or calling APIs."""
    if not get_settings().dry_run:
        raise PermissionError("Mock Tier 1 research requires DRY_RUN=true.")
    if limit < 0:
        raise ValueError("Research limit cannot be negative.")
    if limit == 0:
        return []

    tiers = ("Tier 1", "Tier 2") if include_tier_two else ("Tier 1",)
    placeholders = ", ".join("?" for _ in tiers)
    query = f"""
        SELECT companies.*, mandates.mandate_type
        FROM companies
        LEFT JOIN mandates ON mandates.id = companies.mandate_id
        WHERE companies.priority_tier IN ({placeholders})
    """
    parameters: list[object] = list(tiers)
    if mandate_id:
        query += " AND companies.mandate_id = ?"
        parameters.append(mandate_id)
    query += " ORDER BY companies.fit_score DESC, companies.company_name"

    results: list[ResearchResult] = []
    with get_connection() as connection:
        companies = [
            dict(row) for row in connection.execute(query, parameters).fetchall()
        ]
        for company in companies:
            contact = _best_contact(connection, company["id"])
            contact_id = str(contact["id"]) if contact else None
            if _already_researched(connection, company["id"], contact_id):
                continue
            result = generate_mock_research(company, contact)
            connection.execute(
                """
                INSERT INTO personalization (
                    id,
                    contact_id,
                    opening_line,
                    fit_rationale,
                    outreach_angle,
                    suggested_cta,
                    research_notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    result.contact_id,
                    result.opening_line,
                    result.fit_rationale,
                    result.outreach_angle,
                    result.suggested_cta,
                    result.research_notes,
                ),
            )
            connection.execute(
                """
                INSERT INTO research_logs (
                    id,
                    company_id,
                    contact_id,
                    research_type,
                    research_summary,
                    personalization_notes,
                    source_urls
                ) VALUES (?, ?, ?, 'mock_tier_1_research', ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    result.company_id,
                    result.contact_id,
                    result.fit_rationale,
                    result.research_notes,
                    json.dumps(result.source_urls),
                ),
            )
            results.append(result)
            if len(results) >= limit:
                break
        connection.commit()
    return results
