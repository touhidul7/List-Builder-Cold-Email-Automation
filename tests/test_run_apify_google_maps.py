"""Tests for the DRY_RUN-only Google Maps mock runner."""

from pathlib import Path
import sqlite3

import pytest

from scripts import db
from scripts.run_apify_google_maps import (
    generate_mock_google_maps_leads,
    run_apify_google_maps_mock,
    save_google_maps_leads,
)


@pytest.fixture
def local_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "google-maps-mock.db"
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
        INSERT INTO source_runs (
            id, mandate_id, provider, source_type, query, status, records_found, records_imported
        ) VALUES (?, ?, ?, ?, ?, ?, 0, 0)
        """,
        (
            "source-run-mock-001",
            "mandate-ontario-cleaning-001",
            "Apify Google Maps",
            "local business scrape",
            "commercial cleaning companies in Ontario",
            "approval_required",
        ),
    )
    connection.commit()
    connection.close()
    monkeypatch.setattr(
        "scripts.run_apify_google_maps.RAW_DATA_DIR",
        tmp_path / "raw",
    )
    return db_path


def test_mock_generator_returns_requested_count() -> None:
    assert len(generate_mock_google_maps_leads("commercial cleaning in Ontario", 7)) == 7


def test_commercial_cleaning_query_returns_cleaning_names() -> None:
    leads = generate_mock_google_maps_leads("commercial cleaning in Ontario", 4)

    assert all(
        any(term in lead.company_name.lower() for term in ("cleaning", "janitorial"))
        for lead in leads
    )


def test_generated_leads_use_fake_example_domains() -> None:
    leads = generate_mock_google_maps_leads("commercial cleaning in Ontario", 3)

    assert all(lead.website and "example-cleaning-" in lead.website for lead in leads)
    assert all(lead.google_maps_url and "maps.example.test" in lead.google_maps_url for lead in leads)


def test_save_google_maps_leads_inserts_non_duplicates(local_db: Path) -> None:
    leads = generate_mock_google_maps_leads("commercial cleaning companies in Ontario", 3)

    inserted = save_google_maps_leads(
        "mandate-ontario-cleaning-001",
        "source-run-mock-001",
        leads,
    )

    assert inserted == 3
    assert save_google_maps_leads(
        "mandate-ontario-cleaning-001",
        "source-run-mock-001",
        leads,
    ) == 0


def test_mock_run_updates_source_run_status(local_db: Path) -> None:
    summary = run_apify_google_maps_mock(
        "mandate-ontario-cleaning-001",
        "source-run-mock-001",
        "commercial cleaning companies in Ontario",
        limit=4,
    )

    assert summary["status"] == "completed_mock"
    with db.get_connection() as connection:
        run = connection.execute(
            "SELECT * FROM source_runs WHERE id = ?",
            ("source-run-mock-001",),
        ).fetchone()
    assert run["status"] == "completed_mock"
    assert run["records_found"] == 4
    assert run["records_imported"] == 4
