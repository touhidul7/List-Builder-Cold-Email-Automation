"""Lead-scoring placeholder."""

from typing import Any


def score_lead(lead: dict[str, Any]) -> int:
    """Calculate a simple local placeholder score capped at 100."""
    score = 0
    score += 30 if lead.get("domain") else 0
    score += 40 if lead.get("email") else 0
    score += 30 if lead.get("verification_status") == "verified" else 0
    return min(score, 100)

