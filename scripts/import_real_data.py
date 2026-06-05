"""Import real, user-supplied lead data into local SQLite.

This module does not call enrichment, verification, email, or provider APIs.
It only stores data supplied by the user in local SQLite.
"""

import uuid
from typing import Any

from pydantic import BaseModel, Field

from scripts.db import get_connection
from scripts.dedupe_leads import find_duplicate_company
from scripts.fingerprint import (
    create_company_fingerprint,
    create_contact_fingerprint,
    extract_root_domain,
)


_EMAIL_STATUSES = {"valid", "catch_all", "risky", "invalid", "unknown", ""}


class RealDataImportSummary(BaseModel):
    """Counts from one local real-data import."""

    mandate_id: str
    companies_inserted: int = 0
    companies_linked_existing: int = 0
    companies_skipped_duplicate: int = 0
    contacts_inserted: int = 0
    contacts_skipped_duplicate: int = 0
    rows_skipped_missing_company: int = 0
    warnings: list[str] = Field(default_factory=list)


def _clean(value: Any) -> str:
    """Normalize uploaded scalar values."""
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "null"} else text


def _bool_int(value: Any) -> int:
    """Convert common CSV truthy values to SQLite integer booleans."""
    return 1 if _clean(value).lower() in {"1", "true", "yes", "y"} else 0


def _email_status(value: Any) -> str:
    """Normalize uploaded email status, defaulting to unknown."""
    status = _clean(value).lower()
    if status not in _EMAIL_STATUSES:
        return "unknown"
    return status or "unknown"


def _find_company_by_domain_or_name(
    connection: object,
    root_domain: str | None,
    company_name: str,
    city: str | None,
) -> str | None:
    """Find an inserted company for contact linking."""
    if root_domain:
        row = connection.execute(
            "SELECT id FROM companies WHERE root_domain = ? LIMIT 1",
            (root_domain,),
        ).fetchone()
        if row:
            return str(row["id"])
    row = connection.execute(
        """
        SELECT id
        FROM companies
        WHERE lower(company_name) = lower(?)
          AND lower(COALESCE(city, '')) = lower(COALESCE(?, ''))
        ORDER BY created_at DESC, rowid DESC
        LIMIT 1
        """,
        (company_name, city),
    ).fetchone()
    return str(row["id"]) if row else None


def _insert_company(
    connection: object,
    mandate_id: str,
    row: dict[str, Any],
    summary: RealDataImportSummary,
) -> str | None:
    """Insert or link one real company row."""
    company_name = _clean(row.get("company_name"))
    if not company_name:
        summary.rows_skipped_missing_company += 1
        return None

    website = _clean(row.get("website")) or None
    root_domain = _clean(row.get("root_domain")) or extract_root_domain(website)
    root_domain = root_domain or None
    city = _clean(row.get("city")) or None
    province = _clean(row.get("province")) or None
    phone = _clean(row.get("phone")) or None
    duplicate = find_duplicate_company(
        company_name=company_name,
        website=website,
        root_domain=root_domain,
        city=city,
        province=province,
        phone=phone,
        google_place_id=_clean(row.get("google_place_id")) or None,
        apollo_company_id=_clean(row.get("apollo_company_id")) or None,
        consulti_company_id=_clean(row.get("consulti_company_id")) or None,
        source_url=_clean(row.get("source_url")) or None,
    )
    high_match = next(
        (match for match in duplicate.matches if match.confidence == "high"),
        None,
    )
    if high_match:
        summary.companies_linked_existing += 1
        return high_match.existing_id

    company_id = str(uuid.uuid4())
    connection.execute(
        """
        INSERT INTO companies (
            id,
            mandate_id,
            company_name,
            website,
            root_domain,
            industry,
            city,
            province,
            country,
            phone,
            source,
            source_url,
            google_place_id,
            apollo_company_id,
            consulti_company_id,
            source_fingerprint
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            company_id,
            mandate_id,
            company_name,
            website,
            root_domain,
            _clean(row.get("industry")) or None,
            city,
            province,
            _clean(row.get("country")) or None,
            phone,
            _clean(row.get("source")) or "manual_csv_import",
            _clean(row.get("source_url")) or None,
            _clean(row.get("google_place_id")) or None,
            _clean(row.get("apollo_company_id")) or None,
            _clean(row.get("consulti_company_id")) or None,
            create_company_fingerprint(company_name, root_domain or website, city, phone),
        ),
    )
    summary.companies_inserted += 1
    if duplicate.matches:
        summary.warnings.append(
            f"Possible duplicate inserted for manual review: {company_name}"
        )
    return company_id


def _insert_contact(
    connection: object,
    company_id: str,
    row: dict[str, Any],
    summary: RealDataImportSummary,
) -> None:
    """Insert one real contact if contact details are present and not duplicate."""
    email = _clean(row.get("email")) or None
    full_name = _clean(row.get("full_name")) or _clean(row.get("contact_name")) or None
    title = _clean(row.get("title")) or None
    if not any((email, full_name, title)):
        return

    if email:
        duplicate = connection.execute(
            "SELECT 1 FROM contacts WHERE lower(email) = lower(?) LIMIT 1",
            (email,),
        ).fetchone()
        if duplicate is not None:
            summary.contacts_skipped_duplicate += 1
            return

    company = connection.execute(
        "SELECT root_domain, website FROM companies WHERE id = ?",
        (company_id,),
    ).fetchone()
    company_domain = None
    if company:
        company_domain = company["root_domain"] or company["website"]
    connection.execute(
        """
        INSERT INTO contacts (
            id,
            company_id,
            full_name,
            title,
            email,
            email_status,
            phone,
            source,
            verification_provider,
            source_fingerprint,
            previously_contacted
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            company_id,
            full_name,
            title,
            email,
            _email_status(row.get("email_status")),
            _clean(row.get("contact_phone")) or None,
            _clean(row.get("contact_source")) or _clean(row.get("source")) or "manual_csv_import",
            _clean(row.get("verification_provider")) or "user_supplied",
            create_contact_fingerprint(email, full_name, company_domain),
            _bool_int(row.get("previously_contacted")),
        ),
    )
    summary.contacts_inserted += 1


def import_real_lead_rows(
    mandate_id: str,
    rows: list[dict[str, Any]],
) -> RealDataImportSummary:
    """Import combined company/contact rows from a user-provided CSV."""
    summary = RealDataImportSummary(mandate_id=mandate_id)
    with get_connection() as connection:
        mandate = connection.execute(
            "SELECT 1 FROM mandates WHERE id = ?",
            (mandate_id,),
        ).fetchone()
        if mandate is None:
            raise ValueError(f"Mandate not found: {mandate_id}")

        for row in rows:
            company_id = _clean(row.get("company_id")) or None
            if company_id:
                exists = connection.execute(
                    "SELECT 1 FROM companies WHERE id = ?",
                    (company_id,),
                ).fetchone()
                if exists is None:
                    summary.warnings.append(f"Unknown company_id skipped: {company_id}")
                    continue
            else:
                company_id = _insert_company(connection, mandate_id, row, summary)
            if company_id:
                _insert_contact(connection, company_id, row, summary)

        connection.commit()
    return summary
