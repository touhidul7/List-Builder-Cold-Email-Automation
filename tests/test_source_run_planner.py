"""Tests for local-only source-run planning."""

from pathlib import Path
import sqlite3

import pytest

from scripts import db
from scripts.mandate_intake import parse_mandate
from scripts.mandate_store import save_mandate
from scripts.source_run_planner import (
    create_source_runs_for_mandate,
    find_source_run_by_id_or_prefix,
)


@pytest.fixture
def local_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "source-runs.db"
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


def test_create_source_runs_for_saved_mandate(local_db: Path) -> None:
    mandate_id = save_mandate(
        parse_mandate(
            "Find 25 acquisition targets for a client who wants to buy "
            "a commercial cleaning company in Ontario."
        )
    )

    runs = create_source_runs_for_mandate(mandate_id)

    assert runs
    assert all(run.mandate_id == mandate_id for run in runs)
    assert all("commercial cleaning" in run.query for run in runs)
    assert all("Ontario" in run.query for run in runs)


def test_paid_steps_create_pending_approvals(local_db: Path) -> None:
    mandate_id = save_mandate(parse_mandate("Find family offices in Toronto."))

    runs = create_source_runs_for_mandate(mandate_id)
    paid_runs = [run for run in runs if run.requires_approval]

    assert paid_runs
    assert all(run.status == "approval_required" for run in paid_runs)
    assert all(run.approval_status == "pending" for run in paid_runs)
    assert all(run.cost_approval_id for run in paid_runs)
    with db.get_connection() as connection:
        approval_count = connection.execute(
            "SELECT COUNT(*) FROM cost_approvals WHERE mandate_id = ? AND approval_status = 'pending'",
            (mandate_id,),
        ).fetchone()[0]
    assert approval_count == len(paid_runs)


def test_no_approvals_mode_still_only_plans_runs(local_db: Path) -> None:
    mandate_id = save_mandate(parse_mandate("Find investors for an Oakville gym."))

    runs = create_source_runs_for_mandate(mandate_id, auto_create_approvals=False)

    assert runs
    assert all(run.cost_approval_id is None for run in runs)
    assert all(run.approval_status is None for run in runs)


def _insert_source_run(source_run_id: str) -> None:
    """Insert one deterministic local source run for lookup tests."""
    with db.get_connection() as connection:
        connection.execute(
            """
            INSERT INTO source_runs (id, mandate_id, provider, source_type, query)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                source_run_id,
                "mandate-ontario-cleaning-001",
                "Apify Google Maps",
                "local business scrape",
                "commercial cleaning companies in Ontario",
            ),
        )
        connection.commit()


def test_source_run_lookup_accepts_full_id(local_db: Path) -> None:
    source_run_id = "416b11cb-1111-4111-8111-111111111111"
    _insert_source_run(source_run_id)

    assert find_source_run_by_id_or_prefix(source_run_id)["id"] == source_run_id


def test_source_run_lookup_accepts_short_prefix(local_db: Path) -> None:
    source_run_id = "416b11cb-2222-4222-8222-222222222222"
    _insert_source_run(source_run_id)

    assert find_source_run_by_id_or_prefix("416b11cb")["id"] == source_run_id


def test_source_run_lookup_returns_none_for_unknown_prefix(local_db: Path) -> None:
    assert find_source_run_by_id_or_prefix("missing") is None


def test_source_run_lookup_rejects_ambiguous_prefix(local_db: Path) -> None:
    _insert_source_run("416b11cb-3333-4333-8333-333333333333")
    _insert_source_run("416b11cb-4444-4444-8444-444444444444")

    with pytest.raises(
        ValueError,
        match="Multiple source runs match this prefix. Use the full ID.",
    ):
        find_source_run_by_id_or_prefix("416b11cb")
