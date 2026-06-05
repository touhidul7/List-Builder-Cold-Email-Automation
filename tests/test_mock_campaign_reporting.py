"""Tests for DRY_RUN-only mock campaign reporting."""

from pathlib import Path
import sqlite3

import pytest

from scripts import db
from scripts.mock_campaign_reporting import generate_mock_campaign_events


@pytest.fixture
def local_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "mock-reporting.db"
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
        INSERT INTO campaigns (id, mandate_id, campaign_name, campaign_status)
        VALUES ('campaign-report-001', 'mandate-ontario-cleaning-001', 'Report Test', 'paused')
        """
    )
    for index in range(1, 16):
        company_id = f"company-report-{index:03d}"
        contact_id = f"contact-report-{index:03d}"
        connection.execute(
            """
            INSERT INTO companies (id, mandate_id, company_name)
            VALUES (?, 'mandate-ontario-cleaning-001', ?)
            """,
            (company_id, f"Report Company {index:03d}"),
        )
        connection.execute(
            """
            INSERT INTO contacts (id, company_id, email, email_status)
            VALUES (?, ?, ?, 'valid')
            """,
            (contact_id, company_id, f"lead{index}@example.test"),
        )
        connection.execute(
            """
            INSERT INTO campaign_leads (
                id, campaign_id, contact_id, smartlead_lead_id, upload_status, approval_status
            ) VALUES (?, 'campaign-report-001', ?, ?, 'uploaded_mock', 'approved')
            """,
            (f"campaign-lead-report-{index:03d}", contact_id, f"mock-sl-{index:03d}"),
        )
    connection.commit()
    connection.close()
    return db_path


def test_mock_events_are_inserted_and_summary_counts_returned(local_db: Path) -> None:
    summary = generate_mock_campaign_events("campaign-report-001")

    assert summary.sent == 15
    assert summary.opened == 7
    assert summary.replied == 3
    assert summary.interested == 1
    assert summary.not_interested == 1
    assert summary.meeting_booked == 1
    assert summary.bounced == 0
    with db.get_connection() as connection:
        event_counts = {
            row["event_type"]: row["count"]
            for row in connection.execute(
                """
                SELECT event_type, COUNT(*) AS count
                FROM outreach_events
                WHERE campaign_id = 'campaign-report-001'
                GROUP BY event_type
                """
            ).fetchall()
        }
    assert event_counts == {
        "sent_mock": 15,
        "opened_mock": 7,
        "replied_mock": 3,
        "interested_mock": 1,
        "not_interested_mock": 1,
        "meeting_booked_mock": 1,
    }


def test_mock_campaign_reporting_does_not_call_external_apis(
    local_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_request(*args: object, **kwargs: object) -> None:
        raise AssertionError("External HTTP request attempted")

    monkeypatch.setattr("requests.sessions.Session.request", fail_request)

    assert generate_mock_campaign_events("campaign-report-001").sent == 15
