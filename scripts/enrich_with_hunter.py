"""Placeholder for a future real Hunter enrichment integration.

TODO: Implement only after credentials, consent/compliance review, and approval
gates are ready.
"""

# Safety rules:
# - Do not call Hunter from this placeholder.
# - Keep mock enrichment as the default workflow.
# - Store only necessary business-contact data.


def enrich_with_hunter(*args: object, **kwargs: object) -> None:
    """Raise until the real integration is intentionally implemented."""
    raise NotImplementedError(
        "Real integration not implemented yet. Use mock/dry-run workflow until credentials and approval gates are ready."
    )
