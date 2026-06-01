"""Initialize the local SQLite database for safe development."""

import argparse
from pathlib import Path

from rich.console import Console
from rich.table import Table

from scripts.db import count_rows, execute_sql_file, get_connection, get_local_db_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "database" / "schema.sql"
SEED_PATH = PROJECT_ROOT / "database" / "seed_test_data.sql"
SUMMARY_TABLES = (
    "mandates",
    "companies",
    "contacts",
    "cost_approvals",
    "campaigns",
    "domains",
    "inboxes",
    "source_runs",
    "lead_scores",
    "research_logs",
    "email_sequences",
    "campaign_leads",
)
console = Console()


def load_schema() -> str:
    """Load the checked-in SQLite-compatible schema."""
    return SCHEMA_PATH.read_text(encoding="utf-8")


def initialize_database(reset: bool = False, seed: bool = False) -> Path:
    """Create or update the local SQLite database only."""
    db_path = get_local_db_path()
    if reset and db_path.exists():
        db_path.unlink()
        console.print(f"Removed existing local database: {db_path}")

    with get_connection(db_path) as connection:
        execute_sql_file(connection, SCHEMA_PATH)
        if seed:
            execute_sql_file(connection, SEED_PATH)

        summary = Table(title="Local SQLite Summary")
        summary.add_column("Table")
        summary.add_column("Rows", justify="right")
        for table_name in SUMMARY_TABLES:
            summary.add_row(table_name, str(count_rows(connection, table_name)))

    console.print(f"Local database ready: {db_path}")
    console.print(summary)
    return db_path


def main() -> None:
    """Parse local initialization options."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete data/local_dev.db before applying the schema.",
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Apply database/seed_test_data.sql after the schema.",
    )
    args = parser.parse_args()
    initialize_database(reset=args.reset, seed=args.seed)


if __name__ == "__main__":
    main()
