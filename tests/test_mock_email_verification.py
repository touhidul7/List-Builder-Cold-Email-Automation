"""Tests for DRY_RUN-only mock email verification."""

from pathlib import Path
import sqlite3

import pytest

from scripts import db
from scripts.mock_email_verification import (
    classify_mock_email,
    is_campaign_approved_status,
    needs_manual_review,
    verify_contacts_mock,
)


@pytest.fixture
def local_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "mock-email-verification.db"
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
    connection.execute(
        """
        INSERT INTO contacts (
            id, company_id, full_name, email, email_status, source, verification_provider
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "contact-mock-info-003",
            "company-lakeshore-003",
            "Local Test Contact",
            "info@lakeshorejanitorial.example",
            "unknown",
            "mock_email_enrichment",
            "mock",
        ),
    )
    connection.commit()
    connection.close()
    return db_path


@pytest.mark.parametrize("email", ("", "missing-at", "test@example.com", "a@invalid.test"))
def test_classify_mock_email_returns_invalid_for_bad_emails(email: str) -> None:
    assert classify_mock_email(email)[0] == "invalid"


@pytest.mark.parametrize("email", ("info@example.com", "contact@example.com", "hello@example.com"))
def test_generic_emails_become_catch_all(email: str) -> None:
    assert classify_mock_email(email)[0] == "catch_all"


@pytest.mark.parametrize(
    "email",
    (
        "alex@example.com",
        "jamie@example.com",
        "taylor@example.com",
        "jordan@example.com",
        "casey@example.com",
    ),
)
def test_named_mock_emails_become_valid(email: str) -> None:
    assert classify_mock_email(email)[0] == "valid"


@pytest.mark.parametrize(
    ("status", "approved"),
    (
        ("valid", True),
        ("catch_all", False),
        ("risky", False),
        ("invalid", False),
        ("unknown", False),
    ),
)
def test_campaign_approval_only_accepts_valid(status: str, approved: bool) -> None:
    assert is_campaign_approved_status(status) is approved


def test_manual_review_only_accepts_catch_all() -> None:
    assert needs_manual_review("catch_all") is True
    assert needs_manual_review("valid") is False
    assert needs_manual_review("risky") is False
    assert needs_manual_review("invalid") is False
    assert needs_manual_review("unknown") is False


def test_verify_contacts_mock_updates_local_contact(local_db: Path) -> None:
    results = verify_contacts_mock()

    assert len(results) == 1
    assert results[0].new_status == "catch_all"
    with db.get_connection() as connection:
        stored = connection.execute(
            "SELECT * FROM contacts WHERE id = ?",
            ("contact-mock-info-003",),
        ).fetchone()
    assert stored["email_status"] == "catch_all"
    assert stored["verification_provider"] == "mock_consulti"
    assert stored["last_verified_at"] is not None


def test_verify_contacts_mock_leaves_real_looking_email_untouched(local_db: Path) -> None:
    with db.get_connection() as connection:
        connection.execute(
            """
            INSERT INTO contacts (
                id, company_id, full_name, email, email_status, source, verification_provider
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "contact-real-looking-004",
                "company-lakeshore-003",
                "Real Looking Contact",
                "person@business.ca",
                "unknown",
                "local_test",
                "mock",
            ),
        )
        connection.commit()

    verify_contacts_mock()

    with db.get_connection() as connection:
        stored = connection.execute(
            "SELECT * FROM contacts WHERE id = ?",
            ("contact-real-looking-004",),
        ).fetchone()
    assert stored["email_status"] == "unknown"
    assert stored["verification_provider"] == "mock"
    assert stored["last_verified_at"] is None
