"""Lead-source planning placeholder."""

from typing import Any


def plan_sources(icp: dict[str, Any]) -> dict[str, Any]:
    """Return an empty source plan that requires human review."""
    return {"icp": icp, "status": "requires_review", "sources": []}

