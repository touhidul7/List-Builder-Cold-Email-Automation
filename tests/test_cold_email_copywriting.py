"""Tests for DRY_RUN-only cold email strategy and copy generation."""

from pathlib import Path
import sqlite3

import pytest

from scripts import db
from scripts.cold_email_copywriting import (
    build_cold_email_strategy,
    generate_mock_email_sequence,
    get_latest_email_sequence,
    save_email_sequence_for_mandate,
)


@pytest.fixture
def local_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "cold-email-copywriting.db"
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


def test_buy_side_strategy_has_confidential_acquisition_angle() -> None:
    strategy = build_cold_email_strategy(
        {
            "id": "mandate-buy-001",
            "mandate_name": "Ontario Cleaning Acquisition Targets",
            "mandate_type": "buy-side acquisition target list",
            "campaign_goal": "book acquisition conversation",
        }
    )

    assert "acquisition" in strategy.offer_angle.lower()
    assert "confidential" in strategy.offer_angle.lower()


def test_investor_strategy_has_investor_angle() -> None:
    strategy = build_cold_email_strategy(
        {
            "id": "mandate-investor-001",
            "mandate_name": "Toronto Family Office Investor Outreach",
            "mandate_type": "investor outreach list",
        }
    )

    assert strategy.audience.startswith("Investors")
    assert "investment" in strategy.offer_angle.lower()


def test_generated_sequence_includes_required_placeholders() -> None:
    strategy = build_cold_email_strategy(
        {
            "id": "mandate-buy-001",
            "mandate_name": "Ontario Cleaning Acquisition Targets",
            "mandate_type": "buy-side acquisition target list",
        }
    )
    sequence = generate_mock_email_sequence(strategy)
    copy = " ".join((sequence.email_1, sequence.email_2, sequence.email_3))

    for placeholder in (
        "{{first_name}}",
        "{{company_name}}",
        "{{opening_line}}",
        "{{fit_rationale}}",
        "{{suggested_cta}}",
    ):
        assert placeholder in copy


def test_generated_sequence_has_unsubscribe_line() -> None:
    strategy = build_cold_email_strategy(
        {
            "id": "mandate-general-001",
            "mandate_name": "Local Outreach",
            "mandate_type": "general lead list",
        }
    )

    assert "not interested" in generate_mock_email_sequence(strategy).unsubscribe_line


def test_save_sequence_inserts_campaign_and_email_sequence(local_db: Path) -> None:
    sequence_id = save_email_sequence_for_mandate("mandate-ontario-cleaning-001")

    with db.get_connection() as connection:
        campaign = connection.execute("SELECT * FROM campaigns").fetchone()
        sequence = connection.execute(
            "SELECT * FROM email_sequences WHERE id = ?",
            (sequence_id,),
        ).fetchone()
    assert campaign["campaign_status"] == "draft"
    assert sequence["campaign_id"] == campaign["id"]
    assert get_latest_email_sequence("mandate-ontario-cleaning-001")["id"] == sequence_id


def test_copywriting_does_not_call_external_apis(
    local_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_request(*args: object, **kwargs: object) -> None:
        raise AssertionError("External HTTP request attempted")

    monkeypatch.setattr("requests.sessions.Session.request", fail_request)

    assert save_email_sequence_for_mandate("mandate-ontario-cleaning-001")
