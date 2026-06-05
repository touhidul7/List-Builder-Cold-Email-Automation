"""Tests for DRY_RUN-only paused Smartlead campaign deployment."""

from pathlib import Path
import sqlite3

import pytest

from scripts import db
from scripts.mock_smartlead_deploy import (
    create_mock_smartlead_campaign,
    get_approved_contacts_for_campaign,
)


@pytest.fixture
def local_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "mock-smartlead.db"
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
        "UPDATE companies SET priority_tier = 'Tier 1', fit_score = 88 WHERE id = 'company-clearview-001'"
    )
    connection.execute(
        "UPDATE companies SET priority_tier = 'Tier 2', fit_score = 70 WHERE id = 'company-northstar-002'"
    )
    connection.execute(
        """
        INSERT INTO contacts (
            id, company_id, full_name, title, email, email_status, source
        ) VALUES
        ('contact-invalid-001', 'company-clearview-001', 'Bad Lead', 'Owner', 'bad@example.test', 'invalid', 'test'),
        ('contact-catchall-001', 'company-clearview-001', 'Catch All', 'Owner', 'info@example.test', 'catch_all', 'test'),
        ('contact-unknown-001', 'company-clearview-001', 'Unknown Lead', 'Owner', 'unknown@example.test', 'unknown', 'test')
        """
    )
    connection.execute(
        """
        INSERT INTO personalization (
            id, contact_id, opening_line, fit_rationale, outreach_angle, suggested_cta
        ) VALUES (
            'personalization-maya-001',
            'contact-maya-001',
            'I noticed your Ontario footprint.',
            'Strong local commercial cleaning fit.',
            'Acquisition conversation',
            'Open to a brief confidential conversation?'
        )
        """
    )
    connection.commit()
    connection.close()
    return db_path


def test_valid_contacts_are_selected_and_lower_quality_statuses_excluded(local_db: Path) -> None:
    leads = get_approved_contacts_for_campaign("mandate-ontario-cleaning-001", limit=10)

    emails = {lead.email for lead in leads}
    assert "maya.patel@clearviewfacility.example" in emails
    assert "daniel.mercer@northstaroffice.example" in emails
    assert "bad@example.test" not in emails
    assert "info@example.test" not in emails
    assert "unknown@example.test" not in emails
    assert leads[0].opening_line == "I noticed your Ontario footprint."


def test_campaign_is_created_paused_and_campaign_leads_inserted(local_db: Path) -> None:
    result = create_mock_smartlead_campaign("mandate-ontario-cleaning-001", limit=10)

    assert result.campaign_status == "paused"
    assert result.smartlead_campaign_id.startswith("mock_sl_campaign_")
    assert result.sequence_attached is True
    assert result.leads_uploaded == 2
    with db.get_connection() as connection:
        uploaded = connection.execute(
            "SELECT COUNT(*) AS count FROM campaign_leads WHERE campaign_id = ?",
            (result.campaign_id,),
        ).fetchone()["count"]
    assert uploaded == 2


def test_mock_smartlead_deploy_does_not_call_external_apis(
    local_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_request(*args: object, **kwargs: object) -> None:
        raise AssertionError("External HTTP request attempted")

    monkeypatch.setattr("requests.sessions.Session.request", fail_request)

    assert create_mock_smartlead_campaign("mandate-ontario-cleaning-001", limit=1)
