"""Lead deduplication helpers."""

from collections.abc import Iterable
from typing import Any


def dedupe_leads(leads: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep the first lead for each non-empty fingerprint."""
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for lead in leads:
        fingerprint = str(lead.get("fingerprint", "")).strip()
        if fingerprint and fingerprint not in seen:
            seen.add(fingerprint)
            unique.append(lead)
    return unique

