"""Tests for local SQLite mandate persistence."""

from pathlib import Path
import sqlite3

import pytest

from scripts import db
from scripts.mandate_intake import parse_mandate
from scripts.mandate_store import get_mandate, list_mandates, save_mandate


@pytest.fixture
def local_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "mandates.db"
    monkeypatch.setattr(db, "LOCAL_DB_PATH", db_path)
    schema_path = Path(__file__).resolve().parents[1] / "database" / "schema.sql"
    connection = sqlite3.connect(db_path)
    connection.executescript(schema_path.read_text(encoding="utf-8"))
    connection.close()
    return db_path


def test_parse_and_save_mandate(local_db: Path) -> None:
    mandate = parse_mandate(
        "Find 25 acquisition targets for a client who wants to buy "
        "a commercial cleaning company in Ontario."
    )

    mandate_id = save_mandate(mandate)
    saved = get_mandate(mandate_id)

    assert saved is not None
    assert saved["industry"] == "commercial cleaning"
    assert saved["geography"] == "Ontario"


def test_list_mandates_returns_saved_item(local_db: Path) -> None:
    mandate_id = save_mandate(parse_mandate("Find family offices in Toronto."))

    mandates = list_mandates()

    assert mandates
    assert mandates[0]["id"] == mandate_id
