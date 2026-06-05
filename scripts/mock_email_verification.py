"""DRY_RUN-only mock email verification for synthetic local contacts."""

from pydantic import BaseModel

from scripts.config import get_settings
from scripts.db import get_connection


_ALLOWED_STATUSES = {"valid", "catch_all", "risky", "invalid", "unknown"}


class MockVerificationResult(BaseModel):
    """One synthetic verification outcome stored only in local SQLite."""

    contact_id: str
    email: str
    old_status: str | None = None
    new_status: str
    verification_provider: str = "mock_consulti"
    reason: str


def classify_mock_email(email: str) -> tuple[str, str]:
    """Classify a synthetic email using deterministic offline rules."""
    normalized = (email or "").strip().lower()
    if not normalized or "@" not in normalized:
        return "invalid", "Email is empty or missing @."
    local_part, domain = normalized.split("@", maxsplit=1)
    if "invalid" in domain or local_part == "test":
        return "invalid", "Email matches an invalid mock pattern."
    if local_part in {"info", "contact", "hello"}:
        return "catch_all", "Generic inbox requires manual review."
    if local_part in {"alex", "jamie", "taylor", "jordan", "casey"}:
        return "valid", "Named mock contact matches a valid pattern."
    if "example" in domain:
        return "valid", "Example domain is approved for local mock verification."
    return "unknown", "No mock verification rule matched."


def _is_fake_or_test_email(email: str) -> bool:
    """Return whether an address is safe to mutate in local mock mode."""
    normalized = email.strip().lower()
    if "@" not in normalized:
        return normalized.startswith("test")
    local_part, domain = normalized.split("@", maxsplit=1)
    return (
        local_part == "test"
        or any(marker in domain for marker in ("example", "test", "invalid", "fake"))
    )


def is_campaign_approved_status(email_status: str) -> bool:
    """Return whether an email may be used by a future campaign workflow."""
    return email_status == "valid"


def needs_manual_review(email_status: str) -> bool:
    """Return whether an email needs a human review before use."""
    return email_status == "catch_all"


def verify_contacts_mock(
    mandate_id: str | None = None,
    limit: int = 100,
) -> list[MockVerificationResult]:
    """Verify synthetic local contacts without calling any provider."""
    if not get_settings().dry_run:
        raise PermissionError("Mock email verification requires DRY_RUN=true.")
    if limit < 0:
        raise ValueError("Mock verification limit cannot be negative.")
    if limit == 0:
        return []

    query = """
        SELECT contacts.*
        FROM contacts
        JOIN companies ON companies.id = contacts.company_id
        WHERE contacts.email IS NOT NULL
          AND trim(contacts.email) != ''
          AND (
              contacts.email_status IS NULL
              OR contacts.email_status != 'valid'
              OR contacts.verification_provider IS NULL
              OR contacts.verification_provider = 'mock'
          )
    """
    parameters: list[object] = []
    if mandate_id:
        query += " AND companies.mandate_id = ?"
        parameters.append(mandate_id)
    query += " ORDER BY contacts.email, contacts.id"

    results: list[MockVerificationResult] = []
    with get_connection() as connection:
        contacts = [
            dict(row) for row in connection.execute(query, parameters).fetchall()
        ]
        for contact in contacts:
            email = str(contact["email"])
            if not _is_fake_or_test_email(email):
                continue
            new_status, reason = classify_mock_email(email)
            if new_status not in _ALLOWED_STATUSES:
                raise ValueError(f"Unsupported mock email status: {new_status}")
            result = MockVerificationResult(
                contact_id=contact["id"],
                email=email,
                old_status=contact["email_status"],
                new_status=new_status,
                reason=reason,
            )
            connection.execute(
                """
                UPDATE contacts
                SET
                    email_status = ?,
                    verification_provider = ?,
                    last_verified_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    result.new_status,
                    result.verification_provider,
                    result.contact_id,
                ),
            )
            results.append(result)
            if len(results) >= limit:
                break
        connection.commit()
    return results
