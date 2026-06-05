"""Tests for DRY_RUN-only Tier 1 mock research."""

from pathlib import Path
import sqlite3

import pytest

from scripts import db
from scripts.research_best_leads import generate_mock_research, research_tier_one_leads


@pytest.fixture
def local_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "research-best-leads.db"
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
        UPDATE companies
        SET priority_tier = CASE id
            WHEN 'company-clearview-001' THEN 'Tier 1'
            WHEN 'company-northstar-002' THEN 'Tier 2'
            ELSE 'Tier 3'
        END
        """
    )
    connection.commit()
    connection.close()
    return db_path


def test_generate_mock_research_creates_opening_line_and_cta() -> None:
    result = generate_mock_research(
        {
            "id": "company-local-001",
            "company_name": "Example Cleaning Group",
            "industry": "Commercial cleaning",
            "city": "Toronto",
            "province": "Ontario",
            "mandate_type": "buy-side acquisition target list",
            "priority_tier": "Tier 1",
            "fit_score": 88,
        }
    )

    assert "Example Cleaning Group" in result.opening_line
    assert "Toronto/Ontario" in result.opening_line
    assert result.suggested_cta == "Open to a brief confidential conversation next week?"


def test_research_only_includes_tier_one_by_default(local_db: Path) -> None:
    results = research_tier_one_leads()

    assert [result.priority_tier for result in results] == ["Tier 1"]


def test_include_tier_two_adds_tier_two_leads(local_db: Path) -> None:
    results = research_tier_one_leads(include_tier_two=True)

    assert {result.priority_tier for result in results} == {"Tier 1", "Tier 2"}


def test_research_inserts_personalization_records(local_db: Path) -> None:
    results = research_tier_one_leads()

    with db.get_connection() as connection:
        count = connection.execute("SELECT COUNT(*) FROM personalization").fetchone()[0]
    assert count == len(results)


def test_research_inserts_research_logs(local_db: Path) -> None:
    results = research_tier_one_leads()

    with db.get_connection() as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM research_logs WHERE research_type = ?",
            ("mock_tier_1_research",),
        ).fetchone()[0]
    assert count == len(results)


def test_research_skips_existing_personalization(local_db: Path) -> None:
    assert research_tier_one_leads()

    assert research_tier_one_leads() == []


def test_research_does_not_call_external_apis(
    local_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_request(*args: object, **kwargs: object) -> None:
        raise AssertionError("External HTTP request attempted")

    monkeypatch.setattr("requests.sessions.Session.request", fail_request)

    assert research_tier_one_leads()
