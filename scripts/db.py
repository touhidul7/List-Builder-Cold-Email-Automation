"""Local SQLite helpers for testing the Turso-compatible schema."""

from pathlib import Path
import re
import sqlite3
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCAL_DB_PATH = PROJECT_ROOT / "data" / "local_dev.db"
_SQL_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def get_local_db_path() -> Path:
    """Return the path used for local SQLite development data."""
    return LOCAL_DB_PATH


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Open a local SQLite connection with foreign keys enabled."""
    path = db_path or get_local_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def execute_sql_file(connection: sqlite3.Connection, sql_file_path: Path) -> None:
    """Execute a checked-in SQL file and commit its changes."""
    connection.executescript(sql_file_path.read_text(encoding="utf-8"))
    connection.commit()


def table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    """Return whether a table exists in the connected SQLite database."""
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def count_rows(connection: sqlite3.Connection, table_name: str) -> int:
    """Count table rows after validating the SQL identifier."""
    if not _SQL_IDENTIFIER.fullmatch(table_name):
        raise ValueError(f"Invalid table name: {table_name!r}")
    if not table_exists(connection, table_name):
        return 0
    row = connection.execute(f'SELECT COUNT(*) AS count FROM "{table_name}"').fetchone()
    return int(row["count"])
