"""Tests for DRY_RUN-only mock email enrichment."""

from pathlib import Path
import sqlite3

import pytest

from scripts import db
from scripts.mock_email_enrichment import (
    enrich_companies_without_contacts,
    generate_mock_contact_for_company,
    safe_email_domain,
)


@pytest.fixture
def local_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "mock-email-enrichment.db"
    monkeypatch.setattr(db, "LOCAL_DB_PATH", db_path)
    project_root = Path(__file__).resolve().parents[1]
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(
        (project_root / "database" / "schema.sql").read_text(encoding="utf-8")
    )
    connection.executescript(
        (project_root / "database" / "seed_test_data.sql").read_text(encoding="utf-8")
    )
    connection.commit()
    connection.close()
    return db_path


def test_safe_email_domain_returns_root_domain() -> None:
    assert safe_email_domain("example-cleaning-1.ca", None) == "example-cleaning-1.ca"
    assert safe_email_domain(None, "https://www.example-cleaning-2.ca/services") == (
        "example-cleaning-2.ca"
    )
    assert safe_email_domain(None, None) == "example.com"


def test_generate_mock_contact_for_company_creates_email() -> None:
    contact = generate_mock_contact_for_company(
        {
            "id": "company-mock-001",
            "company_name": "Example Cleaning Group",
            "industry": "Commercial cleaning",
            "website": "https://example-cleaning-1.ca",
            "root_domain": "example-cleaning-1.ca",
        }
    )

    assert contact.email
    assert contact.email.endswith("@example-cleaning-1.ca")
    assert contact.title in {"Owner", "President"}


def test_enrichment_inserts_contacts_for_companies_without_contacts(local_db: Path) -> None:
    contacts = enrich_companies_without_contacts()

    assert contacts
    with db.get_connection() as connection:
        stored = connection.execute(
            "SELECT * FROM contacts WHERE source = ?",
            ("mock_email_enrichment",),
        ).fetchall()
    assert len(stored) == len(contacts)
    assert all(row["verification_provider"] == "mock" for row in stored)


def test_duplicate_email_is_skipped(
    local_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    company = {
        "id": "company-lakeshore-003",
        "company_name": "Lakeshore Janitorial Services",
        "industry": "Commercial cleaning",
        "website": "https://lakeshorejanitorial.example",
        "root_domain": "lakeshorejanitorial.example",
    }
    duplicate = generate_mock_contact_for_company(company)
    with db.get_connection() as connection:
        connection.execute(
            """
            INSERT INTO contacts (id, company_id, full_name, email, source)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "contact-duplicate-email-001",
                "company-clearview-001",
                "Existing Contact",
                duplicate.email,
                "seed",
            ),
        )
        connection.commit()

    contacts = enrich_companies_without_contacts()

    assert all(contact.company_id != company["id"] for contact in contacts)


def test_enrichment_does_not_call_external_apis(
    local_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_request(*args: object, **kwargs: object) -> None:
        raise AssertionError("External HTTP request attempted")

    monkeypatch.setattr("requests.sessions.Session.request", fail_request)

    assert enrich_companies_without_contacts(limit=1)
