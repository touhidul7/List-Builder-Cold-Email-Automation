"""Tests for local SQLite existing-lead checks."""

from pathlib import Path
import sqlite3

import pytest

from scripts import db
from scripts.check_existing_leads import check_existing_leads


@pytest.fixture
def seeded_local_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "existing-leads.db"
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
    connection.close()
    return db_path


def test_commercial_cleaning_ontario_returns_matches(seeded_local_db: Path) -> None:
    summary = check_existing_leads("commercial cleaning", "Ontario")

    assert summary.matching_companies >= 1
    assert summary.recommendation
    assert isinstance(summary.usable_existing_leads, int)


def test_unknown_industry_and_geography_return_no_matches(
    seeded_local_db: Path,
) -> None:
    summary = check_existing_leads("unknown industry", "unknown geography")

    assert summary.matching_companies == 0
    assert summary.matched_company_examples == []
