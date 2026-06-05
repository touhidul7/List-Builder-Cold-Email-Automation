"""Tests for the deterministic SOP lead scoring engine."""

from pathlib import Path
import sqlite3

import pytest

from scripts import db
from scripts.mandate_intake import parse_mandate
from scripts.mandate_store import save_mandate
from scripts.mock_email_enrichment import enrich_companies_without_contacts
from scripts.mock_email_verification import verify_contacts_mock
from scripts.run_apify_google_maps import run_apify_google_maps_mock
from scripts.score_leads import (
    calculate_company_score,
    get_latest_active_mandate_id,
    get_priority_tier,
    is_blocked_or_low_quality_source,
    score_all_companies,
)
from scripts.source_run_planner import create_source_runs_for_mandate


@pytest.fixture
def local_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "score-leads.db"
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


@pytest.mark.parametrize(
    ("score", "expected"),
    [(100, "Tier 1"), (80, "Tier 1"), (79, "Tier 2"), (60, "Tier 2"), (59, "Tier 3"), (40, "Tier 3"), (39, "Reject")],
)
def test_get_priority_tier(score: int, expected: str) -> None:
    assert get_priority_tier(score) == expected


def test_valid_email_increases_email_quality() -> None:
    breakdown = calculate_company_score(
        {"id": "company-1", "company_name": "Example Cleaning", "industry": "cleaning"},
        [{"email": "owner@example.test", "email_status": "valid"}],
        {"industry": "cleaning", "geography": "unknown"},
    )

    assert breakdown.email_quality == 10


@pytest.mark.parametrize("source", ["LinkedIn", "https://example.test/directory/listings", "Yelp"])
def test_blocked_directory_source_is_detected(source: str) -> None:
    assert is_blocked_or_low_quality_source(source)


def test_strong_local_company_scores_at_least_60() -> None:
    breakdown = calculate_company_score(
        {
            "id": "company-2",
            "company_name": "Clearview Facility Cleaning",
            "industry": "commercial cleaning",
            "website": "https://clearview.example",
            "root_domain": "clearview.example",
            "phone": "+1-416-555-0101",
            "city": "Toronto",
            "province": "Ontario",
            "country": "Canada",
            "source": "google_maps",
            "source_url": "https://maps.example/clearview",
        },
        [
            {
                "full_name": "Maya Patel",
                "title": "Owner",
                "email": "maya@clearview.example",
                "email_status": "valid",
            }
        ],
        {
            "mandate_type": "buy-side acquisition target list",
            "industry": "commercial cleaning",
            "geography": "Ontario",
        },
    )

    assert breakdown.total_score >= 60


def test_total_equals_component_sum_and_is_capped() -> None:
    breakdown = calculate_company_score(
        {
            "id": "company-3",
            "company_name": "Regional HVAC Services",
            "industry": "HVAC",
            "website": "https://hvac.example",
            "phone": "+1-416-555-0102",
            "province": "Ontario",
            "country": "Canada",
            "source": "apollo",
            "source_url": "https://apollo.example/hvac",
        },
        [{"full_name": "Ava Chen", "title": "CEO", "email": "ava@hvac.example", "email_status": "valid"}],
        {"mandate_type": "buy-side acquisition target list", "industry": "HVAC", "geography": "Ontario"},
    )

    component_total = (
        breakdown.icp_fit
        + breakdown.geography_fit
        + breakdown.company_size_fit
        + breakdown.contact_quality
        + breakdown.email_quality
        + breakdown.source_confidence
        + breakdown.strategic_relevance
    )
    assert breakdown.total_score == component_total
    assert breakdown.total_score <= 100


def test_latest_mandate_scores_imported_mock_google_maps_companies(local_db: Path) -> None:
    mandate_id = save_mandate(
        parse_mandate(
            "Find 25 acquisition targets for a client who wants to buy a commercial cleaning company in Ontario."
        )
    )
    runs = create_source_runs_for_mandate(mandate_id)
    maps_run = next(run for run in runs if "maps" in run.provider.lower())
    run_apify_google_maps_mock(
        mandate_id,
        maps_run.source_run_id,
        maps_run.query,
        limit=4,
    )
    enrich_companies_without_contacts(mandate_id=mandate_id, limit=4)
    verify_contacts_mock(mandate_id=mandate_id, limit=10)

    scored = score_all_companies()

    assert get_latest_active_mandate_id() == mandate_id
    assert len(scored) == 4
    with db.get_connection() as connection:
        linked_scores = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM lead_scores
            JOIN companies ON companies.id = lead_scores.company_id
            WHERE companies.mandate_id = ?
            """,
            (mandate_id,),
        ).fetchone()["count"]
        total_scores = connection.execute("SELECT COUNT(*) AS count FROM lead_scores").fetchone()["count"]
    assert linked_scores == 4
    assert total_scores > 3
