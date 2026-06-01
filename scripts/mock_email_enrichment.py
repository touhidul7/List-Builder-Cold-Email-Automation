"""DRY_RUN-only mock contact enrichment for local companies."""

import hashlib
import re
import uuid

from pydantic import BaseModel

from scripts.config import get_settings
from scripts.db import get_connection
from scripts.fingerprint import create_contact_fingerprint, extract_root_domain


_CONTACT_NAMES = (
    "Alex Morgan",
    "Jamie Patel",
    "Taylor Brooks",
    "Jordan Singh",
    "Casey Wilson",
)
_EMAIL_STATUSES = ("valid", "catch_all", "unknown")


class MockEnrichedContact(BaseModel):
    """Synthetic contact generated without calling an enrichment provider."""

    company_id: str
    company_name: str
    full_name: str | None = None
    title: str | None = None
    email: str | None = None
    email_status: str = "unknown"
    source: str = "mock_email_enrichment"
    enrichment_provider: str = "mock"


def safe_email_domain(root_domain: str | None, website: str | None) -> str:
    """Return a usable email domain for local mock records."""
    domain = extract_root_domain(root_domain or website)
    return domain or "example.com"


def _stable_index(company: dict, salt: str, size: int) -> int:
    """Choose a deterministic mock variant from company identity."""
    identity = f"{company.get('id', '')}|{company.get('company_name', '')}|{salt}"
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % size


def _mock_title(company: dict) -> str:
    """Select a plausible local-only title from company signals."""
    signals = " ".join(
        str(company.get(field) or "")
        for field in ("company_name", "industry", "source", "source_url")
    ).lower()
    if any(term in signals for term in ("investor", "family office", "private capital")):
        titles = ("Managing Partner", "Principal")
    elif any(
        term in signals
        for term in (
            "local",
            "cleaning",
            "janitorial",
            "gym",
            "fitness",
            "roofing",
            "hvac",
            "dental",
        )
    ):
        titles = ("Owner", "President")
    else:
        titles = ("Founder",)
    return titles[_stable_index(company, "title", len(titles))]


def generate_mock_contact_for_company(company: dict) -> MockEnrichedContact:
    """Generate one deterministic fake contact for a local company."""
    full_name = _CONTACT_NAMES[_stable_index(company, "name", len(_CONTACT_NAMES))]
    first_name = re.sub(r"[^a-z0-9]", "", full_name.split()[0].lower())
    domain = safe_email_domain(company.get("root_domain"), company.get("website"))
    return MockEnrichedContact(
        company_id=str(company["id"]),
        company_name=str(company["company_name"]),
        full_name=full_name,
        title=_mock_title(company),
        email=f"{first_name}@{domain}",
        email_status=_EMAIL_STATUSES[
            _stable_index(company, "email_status", len(_EMAIL_STATUSES))
        ],
    )


def enrich_companies_without_contacts(
    mandate_id: str | None = None,
    limit: int = 25,
) -> list[MockEnrichedContact]:
    """Create synthetic contacts for local companies lacking any contacts."""
    if not get_settings().dry_run:
        raise PermissionError("Mock email enrichment requires DRY_RUN=true.")
    if limit < 0:
        raise ValueError("Mock enrichment limit cannot be negative.")

    query = """
        SELECT companies.*
        FROM companies
        WHERE NOT EXISTS (
            SELECT 1 FROM contacts WHERE contacts.company_id = companies.id
        )
    """
    parameters: list[object] = []
    if mandate_id:
        query += " AND companies.mandate_id = ?"
        parameters.append(mandate_id)
    query += " ORDER BY companies.company_name, companies.id LIMIT ?"
    parameters.append(limit)

    created: list[MockEnrichedContact] = []
    with get_connection() as connection:
        companies = [
            dict(row) for row in connection.execute(query, parameters).fetchall()
        ]
        for company in companies:
            contact = generate_mock_contact_for_company(company)
            duplicate = connection.execute(
                "SELECT 1 FROM contacts WHERE lower(email) = lower(?)",
                (contact.email,),
            ).fetchone()
            if duplicate is not None:
                continue
            connection.execute(
                """
                INSERT INTO contacts (
                    id,
                    company_id,
                    full_name,
                    title,
                    email,
                    email_status,
                    source,
                    verification_provider,
                    source_fingerprint,
                    last_enriched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    str(uuid.uuid4()),
                    contact.company_id,
                    contact.full_name,
                    contact.title,
                    contact.email,
                    contact.email_status,
                    contact.source,
                    contact.enrichment_provider,
                    create_contact_fingerprint(
                        contact.email,
                        contact.full_name,
                        safe_email_domain(company.get("root_domain"), company.get("website")),
                    ),
                ),
            )
            created.append(contact)
        connection.commit()
    return created
