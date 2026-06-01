"""Deterministic local lead scoring using the SOP scoring model."""

from typing import Any

from pydantic import BaseModel

from scripts.db import get_connection


class LeadScoreBreakdown(BaseModel):
    """Reviewable component scores for one company."""

    company_id: str
    company_name: str
    icp_fit: int
    geography_fit: int
    company_size_fit: int
    contact_quality: int
    email_quality: int
    source_confidence: int
    strategic_relevance: int
    total_score: int
    priority_tier: str
    score_reason: str


_LOW_QUALITY_SOURCE_TERMS = (
    "facebook",
    "instagram",
    "linkedin",
    "yelp",
    "yellowpages",
    "zoominfo",
    "crunchbase",
    "axial",
    "glassdoor",
    "indeed",
    "directory",
    "listings",
    "blog",
    "article",
)

_HIGH_CONFIDENCE_SOURCES = {
    "google_maps",
    "apollo",
    "consulti",
    "apify_google_maps",
    "apify_leads_finder",
}


def get_priority_tier(total_score: int) -> str:
    """Map a total score to its SOP priority tier."""
    if total_score >= 80:
        return "Tier 1"
    if total_score >= 60:
        return "Tier 2"
    if total_score >= 40:
        return "Tier 3"
    return "Reject"


def is_blocked_or_low_quality_source(value: str | None) -> bool:
    """Identify blocked social, directory, listing, and article sources."""
    lowered = (value or "").lower()
    return any(term in lowered for term in _LOW_QUALITY_SOURCE_TERMS)


def _text(*values: Any) -> str:
    """Normalize optional values for case-insensitive rule matching."""
    return " ".join(str(value).lower() for value in values if value)


def _geography_score(company: dict, mandate: dict | None) -> int:
    """Score exact geography matches before same-country fallbacks."""
    geography = _text((mandate or {}).get("geography"))
    if not geography or geography == "unknown":
        return 5

    province = _text(company.get("province"))
    city = _text(company.get("city"))
    country = _text(company.get("country"))
    if any(value and value in geography for value in (province, city)):
        return 15
    if geography in province or geography in city:
        return 15
    if country and country in geography:
        return 8
    return 0


def _strategic_relevance(company: dict, mandate: dict | None) -> int:
    """Score acquisition and investor relevance using local text signals."""
    mandate_type = _text((mandate or {}).get("mandate_type"))
    company_text = _text(
        company.get("company_name"),
        company.get("industry"),
        company.get("source"),
        company.get("source_url"),
    )
    if "acquisition" in mandate_type:
        if any(term in company_text for term in ("local", "regional", "independent")):
            return 5
        if company.get("city") or company.get("province"):
            return 5
    if "investor" in mandate_type and any(
        term in company_text
        for term in ("investor", "family office", "private capital", "investment")
    ):
        return 5
    return 2


def calculate_company_score(
    company: dict,
    contacts: list[dict],
    mandate: dict | None = None,
    icp: dict | None = None,
) -> LeadScoreBreakdown:
    """Calculate one deterministic SOP score without external enrichment."""
    del icp  # Reserved for later rule expansion.
    mandate = mandate or {}
    source_text = _text(company.get("source"), company.get("source_url"))
    company_text = _text(
        company.get("company_name"),
        company.get("industry"),
        company.get("source"),
        company.get("source_url"),
    )
    blocked_source = is_blocked_or_low_quality_source(source_text)

    icp_fit = 0
    mandate_industry = _text(mandate.get("industry"))
    if mandate_industry and mandate_industry != "unknown" and mandate_industry in company_text:
        icp_fit += 20
    has_website = bool(company.get("website") or company.get("root_domain"))
    if has_website and not blocked_source:
        icp_fit += 10
    if any(
        term in company_text
        for term in (
            "service",
            "cleaning",
            "janitorial",
            "facility",
            "hvac",
            "roofing",
            "dental",
            "legal",
            "fitness",
            "invest",
        )
    ):
        icp_fit += 5
    icp_fit = min(icp_fit, 35)

    geography_fit = min(_geography_score(company, mandate), 15)

    has_phone = bool(company.get("phone"))
    if has_phone and has_website:
        company_size_fit = 10
    elif has_website:
        company_size_fit = 7
    elif has_phone:
        company_size_fit = 5
    else:
        company_size_fit = 2

    if any(contact.get("full_name") and contact.get("title") for contact in contacts):
        contact_quality = 10
    elif any(contact.get("full_name") for contact in contacts):
        contact_quality = 7
    elif any(contact.get("email") for contact in contacts):
        contact_quality = 5
    else:
        contact_quality = 0

    statuses = {_text(contact.get("email_status")) for contact in contacts}
    if "valid" in statuses:
        email_quality = 10
    elif "catch_all" in statuses:
        email_quality = 6
    elif any(contact.get("email") and not contact.get("email_status") for contact in contacts):
        email_quality = 4
    else:
        email_quality = 0

    source = _text(company.get("source"))
    source_confidence = 8 if source in _HIGH_CONFIDENCE_SOURCES else 0
    if company.get("source_url"):
        source_confidence += 2
    if blocked_source:
        source_confidence = min(source_confidence, 5)
    source_confidence = min(source_confidence, 10)

    strategic_relevance = min(_strategic_relevance(company, mandate), 5)
    total_score = min(
        icp_fit
        + geography_fit
        + company_size_fit
        + contact_quality
        + email_quality
        + source_confidence
        + strategic_relevance,
        100,
    )
    priority_tier = get_priority_tier(total_score)
    score_reason = (
        f"{priority_tier}: ICP {icp_fit}/35, geography {geography_fit}/15, "
        f"size proxy {company_size_fit}/15, contact {contact_quality}/10, "
        f"email {email_quality}/10, source {source_confidence}/10, "
        f"strategic relevance {strategic_relevance}/5."
    )
    return LeadScoreBreakdown(
        company_id=str(company["id"]),
        company_name=str(company["company_name"]),
        icp_fit=icp_fit,
        geography_fit=geography_fit,
        company_size_fit=company_size_fit,
        contact_quality=contact_quality,
        email_quality=email_quality,
        source_confidence=source_confidence,
        strategic_relevance=strategic_relevance,
        total_score=total_score,
        priority_tier=priority_tier,
        score_reason=score_reason,
    )


def _matching_companies(connection: Any, mandate: dict) -> list[dict]:
    """Load linked companies, falling back to local industry/geography matching."""
    linked = connection.execute(
        "SELECT * FROM companies WHERE mandate_id = ? ORDER BY company_name",
        (mandate["id"],),
    ).fetchall()
    if linked:
        return [dict(row) for row in linked]

    industry = _text(mandate.get("industry"))
    geography = _text(mandate.get("geography"))
    rows = connection.execute(
        """
        SELECT *
        FROM companies
        WHERE (
            lower(COALESCE(industry, '')) LIKE ?
            OR lower(company_name) LIKE ?
            OR lower(COALESCE(source, '')) LIKE ?
            OR lower(COALESCE(source_url, '')) LIKE ?
        )
        AND (
            lower(COALESCE(province, '')) LIKE ?
            OR lower(COALESCE(city, '')) LIKE ?
            OR lower(COALESCE(country, '')) LIKE ?
            OR ? LIKE '%' || lower(COALESCE(province, '')) || '%'
            OR ? LIKE '%' || lower(COALESCE(country, '')) || '%'
        )
        ORDER BY company_name
        """,
        (
            f"%{industry}%",
            f"%{industry}%",
            f"%{industry}%",
            f"%{industry}%",
            f"%{geography}%",
            f"%{geography}%",
            f"%{geography}%",
            geography,
            geography,
        ),
    ).fetchall()
    return [dict(row) for row in rows]


def score_companies_for_mandate(mandate_id: str) -> list[LeadScoreBreakdown]:
    """Score local companies for one stored mandate and persist the results."""
    with get_connection() as connection:
        mandate_row = connection.execute(
            "SELECT * FROM mandates WHERE id = ?",
            (mandate_id,),
        ).fetchone()
        if mandate_row is None:
            raise ValueError(f"Mandate not found: {mandate_id}")
        mandate = dict(mandate_row)
        breakdowns: list[LeadScoreBreakdown] = []
        for company in _matching_companies(connection, mandate):
            contacts = [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM contacts WHERE company_id = ?",
                    (company["id"],),
                ).fetchall()
            ]
            breakdown = calculate_company_score(company, contacts, mandate)
            breakdowns.append(breakdown)
            connection.execute(
                """
                INSERT OR REPLACE INTO lead_scores (
                    id,
                    company_id,
                    icp_fit,
                    geography_fit,
                    company_size_fit,
                    contact_quality,
                    email_quality,
                    source_confidence,
                    strategic_relevance,
                    total_score,
                    priority_tier,
                    score_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"lead-score-{breakdown.company_id}",
                    breakdown.company_id,
                    breakdown.icp_fit,
                    breakdown.geography_fit,
                    breakdown.company_size_fit,
                    breakdown.contact_quality,
                    breakdown.email_quality,
                    breakdown.source_confidence,
                    breakdown.strategic_relevance,
                    breakdown.total_score,
                    breakdown.priority_tier,
                    breakdown.score_reason,
                ),
            )
            connection.execute(
                """
                UPDATE companies
                SET
                    fit_score = ?,
                    confidence_score = ?,
                    priority_tier = ?,
                    score_reason = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    breakdown.total_score,
                    breakdown.source_confidence,
                    breakdown.priority_tier,
                    breakdown.score_reason,
                    breakdown.company_id,
                ),
            )
        connection.commit()
    return sorted(breakdowns, key=lambda breakdown: breakdown.total_score, reverse=True)


def score_all_seed_companies() -> list[LeadScoreBreakdown]:
    """Score companies using the first local mandate for development testing."""
    with get_connection() as connection:
        mandate = connection.execute(
            "SELECT id FROM mandates ORDER BY created_at, rowid LIMIT 1"
        ).fetchone()
    if mandate is None:
        raise ValueError("No local mandate found. Seed or save a mandate first.")
    return score_companies_for_mandate(str(mandate["id"]))
