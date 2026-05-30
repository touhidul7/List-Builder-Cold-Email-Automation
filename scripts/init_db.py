"""Database initialization placeholder."""

from pathlib import Path


SCHEMA_PATH = Path(__file__).resolve().parents[1] / "database" / "schema.sql"


def load_schema() -> str:
    """Load the checked-in schema without connecting to Turso."""
    return SCHEMA_PATH.read_text(encoding="utf-8")


def initialize_database() -> None:
    """Refuse remote initialization until it is explicitly implemented."""
    raise NotImplementedError("Remote database initialization is not enabled.")

