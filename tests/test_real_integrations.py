"""Tests for real provider integration safety gates and import behavior."""

from pathlib import Path
import sqlite3

import pytest

from scripts import db
from scripts.export_to_smartlead import (
    SmartleadDraftCampaignRequest,
    create_smartlead_draft_campaign_real,
)
from scripts.real_safety import LIVE_CONFIRMATION, require_real_api_enabled
from scripts.run_apollo_search import (
    ApolloPeopleSearchRequest,
    run_apollo_people_search_real,
)


@pytest.fixture
def local_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "real-integrations.db"
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
        INSERT INTO cost_approvals (
            id, mandate_id, action_type, action_description, provider,
            estimated_cost, approval_status, approved_by, approved_at
        ) VALUES (
            'approval-real-001', 'mandate-ontario-cleaning-001', 'real_api',
            'Approved real API test', 'apollo', 1, 'approved', 'tester',
            CURRENT_TIMESTAMP
        )
        """
    )
    connection.commit()
    connection.close()
    return db_path


def _enable_real(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DRY_RUN", "false")
    monkeypatch.setenv("REAL_API_CONFIRMATION", LIVE_CONFIRMATION)
    monkeypatch.setenv("APOLLO_API_KEY", "apollo-key")
    monkeypatch.setenv("SMARTLEAD_API_KEY", "smartlead-key")


def test_real_api_guard_blocks_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DRY_RUN", "true")

    with pytest.raises(PermissionError, match="DRY_RUN=true"):
        require_real_api_enabled("Apollo", "key")


def test_apollo_search_imports_returned_people(
    local_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_real(monkeypatch)

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "people": [
                    {
                        "name": "Ava Real",
                        "title": "Owner",
                        "organization": {
                            "id": "apollo-org-1",
                            "name": "Ava Cleaning",
                            "website_url": "https://avacleaning.ca",
                            "city": "Toronto",
                            "state": "Ontario",
                            "country": "Canada",
                            "industry": "Commercial cleaning",
                        },
                    }
                ]
            }

    def fake_post(*args: object, **kwargs: object) -> Response:
        return Response()

    monkeypatch.setattr("requests.post", fake_post)

    result = run_apollo_people_search_real(
        ApolloPeopleSearchRequest(
            mandate_id="mandate-ontario-cleaning-001",
            approval_id="approval-real-001",
            q_keywords="commercial cleaning",
        )
    )

    assert result.people_returned == 1
    assert result.companies_inserted == 1
    assert result.contacts_inserted == 1


def test_smartlead_draft_campaign_creates_local_mapping(
    local_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_real(monkeypatch)

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"ok": True, "id": 12345, "name": "Real Draft"}

    def fake_post(*args: object, **kwargs: object) -> Response:
        return Response()

    monkeypatch.setattr("requests.post", fake_post)

    result = create_smartlead_draft_campaign_real(
        SmartleadDraftCampaignRequest(
            mandate_id="mandate-ontario-cleaning-001",
            approval_id="approval-real-001",
            campaign_name="Real Draft",
        )
    )

    assert result.smartlead_campaign_id == "12345"
    assert result.campaign_status == "drafted_external"
