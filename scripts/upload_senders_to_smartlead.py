"""Placeholder for future real Smartlead sender upload.

TODO: Implement only after credentials, sender warmup policy, and approval gates
are ready.
"""

# Safety rules:
# - Do not call Smartlead from this placeholder.
# - Never activate senders automatically.
# - Keep campaigns paused until human approval.


def upload_senders_to_smartlead(*args: object, **kwargs: object) -> None:
    """Raise until the real integration is intentionally implemented."""
    raise NotImplementedError(
        "Real integration not implemented yet. Use mock/dry-run workflow until credentials and approval gates are ready."
    )
