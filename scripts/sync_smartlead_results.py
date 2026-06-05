"""Placeholder for future real Smartlead reporting sync.

TODO: Implement only after credentials, campaign mapping, and safe read-only
sync rules are ready.
"""

# Safety rules:
# - Do not call Smartlead from this placeholder.
# - Treat reporting sync as read-only.
# - Never send, resume, or launch campaigns from reporting code.


def sync_smartlead_results(*args: object, **kwargs: object) -> None:
    """Raise until the real integration is intentionally implemented."""
    raise NotImplementedError(
        "Real integration not implemented yet. Use mock/dry-run workflow until credentials and approval gates are ready."
    )
