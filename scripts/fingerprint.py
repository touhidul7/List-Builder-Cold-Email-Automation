"""Stable local lead fingerprint generation."""

import hashlib


def build_fingerprint(company_name: str, domain: str = "", email: str = "") -> str:
    """Build a deterministic SHA-256 fingerprint from normalized lead fields."""
    normalized = "|".join(
        value.strip().lower() for value in (company_name, domain, email)
    )
    if not normalized.replace("|", ""):
        raise ValueError("At least one lead identifier is required.")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

