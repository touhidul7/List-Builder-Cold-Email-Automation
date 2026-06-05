"""Tests for importing user-supplied real lead data into local SQLite."""

from pathlib import Path
import sqlite3

import pytest

from scripts import db
from scripts.import_real_data import import_real_lead_rows


@pytest.fixture
def local_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "real-import.db"
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


def test_import_real_lead_rows_inserts_company_and_contact(local_db: Path) -> None:
    summary = import_real_lead_rows(
        "mandate-ontario-cleaning-001",
        [
            {
                "company_name": "Real GTA Cleaning",
                "website": "https://realgtacleaning.ca",
                "industry": "Commercial cleaning",
                "city": "Toronto",
                "province": "Ontario",
                "country": "Canada",
                "phone": "416-555-9000",
                "full_name": "Priya Shah",
                "title": "Owner",
                "email": "priya@realgtacleaning.ca",
                "email_status": "valid",
            }
        ],
    )

    assert summary.companies_inserted == 1
    assert summary.contacts_inserted == 1
    with db.get_connection() as connection:
        company = connection.execute(
            "SELECT * FROM companies WHERE company_name = 'Real GTA Cleaning'"
        ).fetchone()
        contact = connection.execute(
            "SELECT * FROM contacts WHERE email = 'priya@realgtacleaning.ca'"
        ).fetchone()
    assert company["source"] == "manual_csv_import"
    assert company["root_domain"] == "realgtacleaning.ca"
    assert contact["email_status"] == "valid"
    assert contact["verification_provider"] == "user_supplied"


def test_duplicate_company_links_contact_to_existing_company(local_db: Path) -> None:
    summary = import_real_lead_rows(
        "mandate-ontario-cleaning-001",
        [
            {
                "company_name": "Clearview Facility Care",
                "website": "https://clearviewfacility.example/contact",
                "full_name": "New Contact",
                "email": "new.contact@clearviewfacility.example",
                "email_status": "unknown",
            }
        ],
    )

    assert summary.companies_inserted == 0
    assert summary.companies_linked_existing == 1
    assert summary.contacts_inserted == 1
    with db.get_connection() as connection:
        contact = connection.execute(
            "SELECT * FROM contacts WHERE email = 'new.contact@clearviewfacility.example'"
        ).fetchone()
    assert contact["company_id"] == "company-clearview-001"


def test_duplicate_contact_email_is_skipped(local_db: Path) -> None:
    summary = import_real_lead_rows(
        "mandate-ontario-cleaning-001",
        [
            {
                "company_name": "Clearview Facility Care",
                "website": "https://clearviewfacility.example",
                "full_name": "Maya Patel",
                "email": "maya.patel@clearviewfacility.example",
            }
        ],
    )

    assert summary.contacts_skipped_duplicate == 1


def test_import_rejects_unknown_mandate(local_db: Path) -> None:
    with pytest.raises(ValueError, match="Mandate not found"):
        import_real_lead_rows("missing-mandate", [{"company_name": "Example"}])
