"""Turso database adapter placeholder."""

from dataclasses import dataclass

from scripts.config import get_settings


@dataclass(frozen=True)
class DatabaseConfig:
    """Connection details for a future Turso adapter."""

    url: str
    auth_token: str


def get_database_config() -> DatabaseConfig:
    """Read Turso settings without opening a connection."""
    settings = get_settings()
    return DatabaseConfig(
        url=settings.turso_database_url,
        auth_token=settings.turso_auth_token,
    )


def connect() -> None:
    """Refuse network access until a Turso adapter is intentionally added."""
    raise NotImplementedError("Turso connectivity is not enabled in this scaffold.")

