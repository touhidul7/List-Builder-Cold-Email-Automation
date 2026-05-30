"""Existing-lead lookup placeholder."""

from collections.abc import Iterable
from typing import Any


def find_existing_leads(
    fingerprints: Iterable[str], known_leads: Iterable[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Return locally supplied leads with matching fingerprints."""
    requested = set(fingerprints)
    return [lead for lead in known_leads if lead.get("fingerprint") in requested]

