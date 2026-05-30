"""Mandate intake placeholder."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Mandate:
    """Minimal client mandate captured before lead work begins."""

    client_name: str
    objective: str


def capture_mandate(client_name: str, objective: str) -> Mandate:
    """Create an in-memory mandate after basic validation."""
    if not client_name.strip() or not objective.strip():
        raise ValueError("Client name and objective are required.")
    return Mandate(client_name=client_name.strip(), objective=objective.strip())

