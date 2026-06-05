"""Tests for the full local dry-run SOP pipeline."""

from pathlib import Path

import pytest

from scripts import db
from scripts.dry_pipeline import run_dry_pipeline


def test_full_dry_pipeline_completes_and_creates_expected_records(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "dry-pipeline.db"
    monkeypatch.setattr(db, "LOCAL_DB_PATH", db_path)

    def fail_request(*args: object, **kwargs: object) -> None:
        raise AssertionError("External HTTP request attempted")

    monkeypatch.setattr("requests.sessions.Session.request", fail_request)

    summary = run_dry_pipeline(
        "Find 25 acquisition targets for a client who wants to buy a commercial cleaning company in Ontario.",
        limit=6,
        reset_db=True,
    )

    assert summary.companies_imported == 6
    assert summary.contacts_created == 6
    assert summary.valid_emails == 6
    assert summary.leads_scored == 6
    assert summary.tier_1_leads > 0
    assert summary.personalization_records > 0
    assert summary.campaign_status == "paused"
    assert summary.smartlead_campaign_id.startswith("mock_sl_campaign_")
    assert summary.campaign_leads_uploaded > 0
    with db.get_connection() as connection:
        counts = {
            table: connection.execute(
                f"SELECT COUNT(*) AS count FROM {table}"
            ).fetchone()["count"]
            for table in (
                "companies",
                "contacts",
                "lead_scores",
                "personalization",
                "campaigns",
                "campaign_leads",
            )
        }
    assert counts["companies"] >= 9
    assert counts["contacts"] >= 8
    assert counts["lead_scores"] >= 6
    assert counts["campaigns"] >= 1
    assert counts["campaign_leads"] > 0
