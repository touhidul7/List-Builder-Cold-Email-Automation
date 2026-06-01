"""Tests for stable local lead fingerprints."""

from scripts.fingerprint import (
    create_company_fingerprint,
    create_contact_fingerprint,
    normalize_domain,
    normalize_phone,
    normalize_text,
)


def test_normalize_domain_handles_url_www_and_path() -> None:
    assert normalize_domain("https://www.example.com/about?source=test") == "example.com"
    assert normalize_domain("example.com/contact") == "example.com"


def test_normalize_phone_removes_symbols_and_country_code() -> None:
    assert normalize_phone("+1 (416) 555-1234") == "4165551234"


def test_normalize_text_lowercases_and_strips_punctuation() -> None:
    assert normalize_text("  ABC, Cleaning!  Services. ") == "abc cleaning services"


def test_company_fingerprint_is_stable_for_normalized_domain() -> None:
    assert create_company_fingerprint(
        "ABC Cleaning",
        "https://www.example.com/about",
        "Toronto",
        "416-555-1234",
    ) == create_company_fingerprint(
        "Different Display Name",
        "example.com/contact",
        "Ottawa",
        "+1 (613) 555-9999",
    )


def test_contact_fingerprint_uses_email_when_available() -> None:
    assert create_contact_fingerprint(
        "Owner@Example.com",
        "First Name",
        "example.com",
    ) == create_contact_fingerprint(
        "owner@example.com",
        "Different Name",
        "other.example",
    )
