"""Stable local normalization and fingerprint helpers."""

import hashlib
import re
from urllib.parse import urlsplit

import tldextract


_EXTRACTOR = tldextract.TLDExtract(cache_dir=None, suffix_list_urls=())


def normalize_text(value: str | None) -> str:
    """Lowercase text, remove punctuation, and collapse whitespace."""
    if value is None:
        return ""
    normalized = re.sub(r"[^\w\s]", " ", value.lower())
    return " ".join(normalized.split())


def normalize_phone(value: str | None) -> str:
    """Return digits only, without a North American leading country code."""
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 11 and digits.startswith("1"):
        return digits[1:]
    return digits


def normalize_domain(url_or_domain: str | None) -> str:
    """Return the normalized root domain without making network requests."""
    value = (url_or_domain or "").strip().lower()
    if not value:
        return ""
    if "://" not in value:
        value = f"https://{value}"
    hostname = (urlsplit(value).hostname or "").removeprefix("www.")
    extracted = _EXTRACTOR(value)
    if extracted.domain and extracted.suffix:
        return f"{extracted.domain}.{extracted.suffix}"
    return hostname


def extract_root_domain(url_or_domain: str | None) -> str:
    """Return the normalized root domain for a URL or domain."""
    return normalize_domain(url_or_domain)


def _sha256(value: str) -> str:
    """Hash a normalized fingerprint payload."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def create_company_fingerprint(
    company_name: str | None,
    website: str | None,
    city: str | None,
    phone: str | None,
) -> str:
    """Create a stable domain-first company fingerprint."""
    domain = normalize_domain(website)
    if domain:
        return _sha256(f"domain:{domain}")
    fallback = "|".join(
        (
            normalize_text(company_name),
            normalize_text(city),
            normalize_phone(phone),
        )
    )
    return _sha256(f"company:{fallback}")


def create_contact_fingerprint(
    email: str | None,
    full_name: str | None,
    company_domain: str | None,
) -> str:
    """Create a stable email-first contact fingerprint."""
    normalized_email = normalize_text(email)
    if normalized_email:
        return _sha256(f"email:{normalized_email}")
    fallback = "|".join(
        (
            normalize_text(full_name),
            normalize_domain(company_domain),
        )
    )
    return _sha256(f"contact:{fallback}")
