"""Safety checks for real external API integrations."""

from scripts.config import get_settings
from scripts.db import get_connection


LIVE_CONFIRMATION = "I_UNDERSTAND_REAL_API_CALLS"


def require_real_api_enabled(provider: str, api_key: str, approval_id: str | None = None) -> None:
    """Require explicit real-mode configuration before external API calls."""
    settings = get_settings()
    if settings.dry_run:
        raise PermissionError(
            f"{provider} real API call blocked because DRY_RUN=true."
        )
    if settings.real_api_confirmation != LIVE_CONFIRMATION:
        raise PermissionError(
            f"{provider} real API call blocked. Set REAL_API_CONFIRMATION={LIVE_CONFIRMATION}."
        )
    if not api_key:
        raise PermissionError(f"{provider} API key is missing.")
    if approval_id:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT approval_status
                FROM cost_approvals
                WHERE id = ?
                """,
                (approval_id,),
            ).fetchone()
        if row is None or row["approval_status"] != "approved":
            raise PermissionError(
                f"{provider} real API call blocked. Cost approval is not approved."
            )
