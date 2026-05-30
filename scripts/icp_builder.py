"""Ideal customer profile builder placeholder."""

from typing import Any


def build_icp(mandate: dict[str, Any]) -> dict[str, Any]:
    """Return a draft ICP container for later enrichment."""
    return {"mandate": mandate, "status": "draft", "criteria": []}

