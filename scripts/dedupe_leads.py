"""Local-only company deduplication checks and previews."""

from collections import defaultdict
from typing import Callable

from pydantic import BaseModel, Field

from scripts.db import get_connection
from scripts.fingerprint import (
    create_company_fingerprint,
    extract_root_domain,
    normalize_domain,
    normalize_phone,
    normalize_text,
)


class DuplicateMatch(BaseModel):
    """One possible match against an existing local company."""

    existing_id: str
    duplicate_type: str
    confidence: str
    reason: str


class CompanyDeduplicationResult(BaseModel):
    """Duplicate decision for one proposed company."""

    is_duplicate: bool
    matches: list[DuplicateMatch] = Field(default_factory=list)
    recommended_action: str


def _add_match(
    matches: list[DuplicateMatch],
    seen: set[tuple[str, str]],
    company_id: str,
    duplicate_type: str,
    confidence: str,
    reason: str,
) -> None:
    """Append a unique match reason for an existing company."""
    key = (company_id, duplicate_type)
    if key not in seen:
        seen.add(key)
        matches.append(
            DuplicateMatch(
                existing_id=company_id,
                duplicate_type=duplicate_type,
                confidence=confidence,
                reason=reason,
            )
        )


def find_duplicate_company(
    company_name: str | None = None,
    website: str | None = None,
    root_domain: str | None = None,
    city: str | None = None,
    province: str | None = None,
    phone: str | None = None,
    google_place_id: str | None = None,
    apollo_company_id: str | None = None,
    consulti_company_id: str | None = None,
    source_url: str | None = None,
) -> CompanyDeduplicationResult:
    """Find matching local companies without mutating or deleting records."""
    del province  # Reserved for future regional tie-breakers.
    proposed_domain = normalize_domain(root_domain or website)
    proposed_phone = normalize_phone(phone)
    proposed_name = normalize_text(company_name)
    proposed_city = normalize_text(city)
    proposed_source_url = (source_url or "").strip().lower()
    matches: list[DuplicateMatch] = []
    seen: set[tuple[str, str]] = set()

    with get_connection() as connection:
        companies = [dict(row) for row in connection.execute("SELECT * FROM companies")]

    for existing in companies:
        company_id = str(existing["id"])
        existing_domain = normalize_domain(existing.get("root_domain") or existing.get("website"))
        if proposed_domain and proposed_domain == existing_domain:
            _add_match(
                matches,
                seen,
                company_id,
                "root_domain",
                "high",
                f"Exact root domain match: {proposed_domain}",
            )
        for duplicate_type, proposed_value, field in (
            ("google_place_id", google_place_id, "google_place_id"),
            ("apollo_company_id", apollo_company_id, "apollo_company_id"),
            ("consulti_company_id", consulti_company_id, "consulti_company_id"),
        ):
            if proposed_value and proposed_value == existing.get(field):
                _add_match(
                    matches,
                    seen,
                    company_id,
                    duplicate_type,
                    "high",
                    f"Exact {duplicate_type} match: {proposed_value}",
                )
        if proposed_phone and proposed_phone == normalize_phone(existing.get("phone")):
            _add_match(
                matches,
                seen,
                company_id,
                "phone",
                "high",
                f"Normalized phone match: {proposed_phone}",
            )
        if (
            proposed_name
            and proposed_city
            and proposed_name == normalize_text(existing.get("company_name"))
            and proposed_city == normalize_text(existing.get("city"))
        ):
            _add_match(
                matches,
                seen,
                company_id,
                "company_name_city",
                "medium",
                f"Normalized company name and city match: {company_name}, {city}",
            )
        if (
            proposed_source_url
            and proposed_source_url == (existing.get("source_url") or "").strip().lower()
        ):
            _add_match(
                matches,
                seen,
                company_id,
                "source_url",
                "medium",
                f"Exact source URL match: {source_url}",
            )

    has_high_confidence = any(match.confidence == "high" for match in matches)
    if has_high_confidence:
        recommended_action = "skip_existing_company"
    elif matches:
        recommended_action = "manual_review"
    else:
        recommended_action = "create_new_company"
    return CompanyDeduplicationResult(
        is_duplicate=bool(matches),
        matches=matches,
        recommended_action=recommended_action,
    )


def update_company_fingerprints() -> int:
    """Populate normalized domains and source fingerprints for local companies."""
    updated = 0
    with get_connection() as connection:
        companies = [dict(row) for row in connection.execute("SELECT * FROM companies")]
        for company in companies:
            root_domain = company.get("root_domain") or extract_root_domain(company.get("website"))
            fingerprint = create_company_fingerprint(
                company.get("company_name"),
                root_domain or company.get("website"),
                company.get("city"),
                company.get("phone"),
            )
            if (
                root_domain != company.get("root_domain")
                or fingerprint != company.get("source_fingerprint")
            ):
                connection.execute(
                    """
                    UPDATE companies
                    SET root_domain = ?, source_fingerprint = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (root_domain or None, fingerprint, company["id"]),
                )
                updated += 1
        connection.commit()
    return updated


def _duplicate_groups(
    companies: list[dict],
    duplicate_type: str,
    key_builder: Callable[[dict], str],
) -> list[dict]:
    """Return duplicate groups for a normalized field key."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    for company in companies:
        key = key_builder(company)
        if key:
            grouped[key].append(company)
    return [
        {
            "duplicate_type": duplicate_type,
            "value": key,
            "company_ids": [str(company["id"]) for company in group],
            "company_names": [str(company["company_name"]) for company in group],
        }
        for key, group in grouped.items()
        if len(group) > 1
    ]


def dedupe_companies_preview() -> list[dict]:
    """Return possible duplicate groups without deleting any local records."""
    with get_connection() as connection:
        companies = [dict(row) for row in connection.execute("SELECT * FROM companies")]
    groups: list[dict] = []
    groups.extend(
        _duplicate_groups(
            companies,
            "root_domain",
            lambda company: normalize_domain(company.get("root_domain") or company.get("website")),
        )
    )
    groups.extend(
        _duplicate_groups(companies, "phone", lambda company: normalize_phone(company.get("phone")))
    )
    groups.extend(
        _duplicate_groups(
            companies,
            "company_name_city",
            lambda company: "|".join(
                (
                    normalize_text(company.get("company_name")),
                    normalize_text(company.get("city")),
                )
            ),
        )
    )
    return groups
