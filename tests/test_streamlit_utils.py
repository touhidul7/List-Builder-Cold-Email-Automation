"""Tests for Streamlit dashboard utility helpers."""

from pathlib import Path
import sqlite3

import pandas as pd
import pytest

from app import utils
from scripts import db


@pytest.fixture
def local_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "streamlit-utils.db"
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


def test_short_id_handles_values() -> None:
    assert utils.short_id("abcdef123456", 6) == "abcdef"
    assert utils.short_id(None) == "-"


def test_ensure_local_db_exists_returns_boolean(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(db, "LOCAL_DB_PATH", tmp_path / "missing.db")
    assert utils.ensure_local_db_exists() is False


def test_get_db_counts_returns_dict(local_db: Path) -> None:
    counts = utils.get_db_counts()

    assert isinstance(counts, dict)
    assert counts["mandates"] == 1
    assert counts["companies"] == 3


def test_fetch_table_returns_dataframe(local_db: Path) -> None:
    df = utils.fetch_table("SELECT id, mandate_name FROM mandates")

    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["id", "mandate_name"]
    assert len(df) == 1


def test_fetch_table_rejects_mutation(local_db: Path) -> None:
    with pytest.raises(ValueError):
        utils.fetch_table("DELETE FROM mandates")
