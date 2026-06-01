"""Tests for local SQLite company duplicate checks."""

from pathlib import Path
import sqlite3

import pytest

from scripts import db
from scripts.dedupe_leads import find_duplicate_company


@pytest.fixture
def local_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "dedupe.db"
    monkeypatch.setattr(db, "LOCAL_DB_PATH", db_path)
    project_root = Path(__file__).resolve().parents[1]
    connection = sqlite3.connect(db_path)
    connection.executescript(
        (project_root / "database" / "schema.sql").read_text(encoding="utf-8")
    )
    connection.execute(
        """
        INSERT INTO companies (
            id, company_name, website, root_domain, city, province, country, phone
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "company-existing",
            "ABC Cleaning",
            "https://www.abccleaning.ca/about",
            "abccleaning.ca",
            "Toronto",
            "Ontario",
            "Canada",
            "+1 (416) 555-1234",
        ),
    )
    connection.commit()
    connection.close()
    return db_path


def test_duplicate_by_root_domain_returns_high_confidence(local_db: Path) -> None:
    result = find_duplicate_company(website="https://abccleaning.ca/contact")

    assert result.is_duplicate
    assert result.recommended_action == "skip_existing_company"
    assert any(match.duplicate_type == "root_domain" and match.confidence == "high" for match in result.matches)


def test_duplicate_by_company_name_and_city_returns_medium_confidence(local_db: Path) -> None:
    result = find_duplicate_company(company_name="ABC, Cleaning!", city="Toronto")

    assert result.is_duplicate
    assert result.recommended_action == "manual_review"
    assert any(match.duplicate_type == "company_name_city" and match.confidence == "medium" for match in result.matches)


def test_no_match_returns_create_new_company(local_db: Path) -> None:
    result = find_duplicate_company(
        company_name="New Facility Care",
        website="https://newfacilitycare.ca",
        city="Ottawa",
    )

    assert not result.is_duplicate
    assert result.recommended_action == "create_new_company"
