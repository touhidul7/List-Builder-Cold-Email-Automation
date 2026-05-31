"""Offline, rule-based mandate intake parsing."""

import re

from pydantic import BaseModel, Field


class Mandate(BaseModel):
    """Structured mandate extracted from a natural-language request."""

    mandate_name: str
    mandate_type: str
    industry: str
    geography: str
    target_lead_count: int
    campaign_goal: str
    company_size: str | None = None
    target_titles: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    raw_prompt: str


_INDUSTRY_PATTERNS = (
    (r"\bcommercial cleaning compan(?:y|ies)\b", "commercial cleaning"),
    (r"\bcleaning compan(?:y|ies)\b", "cleaning"),
    (r"\bfamily offic(?:e|es)\b", "family office"),
    (r"\bprivate equity firms?\b", "private equity firm"),
    (r"\binvestment firms?\b", "investment firm"),
    (r"\bsaas\b", "SaaS"),
    (r"\bsoftware compan(?:y|ies)\b", "software"),
    (r"\btechnology compan(?:y|ies)\b", "technology"),
    (r"\bagenc(?:y|ies)\b", "agency"),
    (r"\bgarden cent(?:re|er)s?\b", "garden centre"),
    (r"\bhvac compan(?:y|ies)\b", "HVAC"),
    (r"\broofing compan(?:y|ies)\b", "roofing"),
    (r"\bdental clinics?\b", "dental clinic"),
    (r"\blaw firms?\b", "law firm"),
    (r"\bgyms?\b", "gym"),
    (r"\binvestors?\b", "investor"),
)

_KNOWN_GEOGRAPHIES = (
    "New York",
    "United States",
    "USA",
    "U.S.",
    "California",
    "Texas",
    "Florida",
    "Ontario",
    "Toronto",
    "Canada",
    "GTA",
    "Oakville",
    "Alberta",
    "British Columbia",
    "Manitoba",
    "New Brunswick",
    "Newfoundland and Labrador",
    "Nova Scotia",
    "Prince Edward Island",
    "Quebec",
    "Saskatchewan",
)


def _extract_target_lead_count(prompt: str) -> int:
    """Extract common requested-list-size phrases."""
    patterns = (
        r"\bfind\s+(\d+)\b",
        r"\bbuild\s+(?:me\s+)?a\s+list\s+of\s+(\d+)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, prompt, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    return 25


def _extract_geography(prompt: str) -> str:
    """Extract a supported geography from location phrases."""
    choices = "|".join(re.escape(value) for value in _KNOWN_GEOGRAPHIES)
    match = re.search(
        rf"\b(?:in|around)\s+(?:the\s+)?({choices})\b",
        prompt,
        flags=re.IGNORECASE,
    )
    if match:
        return _normalize_geography(match.group(1))

    # Handle noun phrases such as "investors for an Oakville gym."
    match = re.search(
        rf"\b(?:an?|the)\s+({choices})\s+[\w-]+",
        prompt,
        flags=re.IGNORECASE,
    )
    if match:
        return _normalize_geography(match.group(1))
    return "unknown"


def _normalize_geography(value: str) -> str:
    """Return consistent display casing for supported geographies."""
    acronyms = {"gta": "GTA", "usa": "USA", "u.s.": "U.S."}
    if value.lower() in acronyms:
        return acronyms[value.lower()]
    return value.title()


def _extract_industry(prompt: str) -> str:
    """Extract the first matching supported industry."""
    for pattern, industry in _INDUSTRY_PATTERNS:
        if re.search(pattern, prompt, flags=re.IGNORECASE):
            return industry
    return "unknown"


def _extract_mandate_type(prompt: str) -> str:
    """Classify the mandate using explicit intent keywords."""
    lowered = prompt.lower()
    if "strategic buyer" in lowered:
        return "strategic buyer list"
    if any(term in lowered for term in ("buy", "acquisition", "acquire", "targets")):
        return "buy-side acquisition target list"
    if any(
        term in lowered for term in ("investor", "capital", "raise", "family office")
    ):
        return "investor outreach list"
    return "general lead list"


def _campaign_goal(mandate_type: str) -> str:
    """Map a mandate type to its default campaign goal."""
    goals = {
        "buy-side acquisition target list": "book acquisition conversation",
        "investor outreach list": "book investor conversation",
        "strategic buyer list": "book strategic buyer conversation",
    }
    return goals.get(mandate_type, "book intro call")


def _display_industry(industry: str) -> str:
    """Format an industry for a generated mandate name."""
    return "HVAC" if industry == "HVAC" else industry.title()


def _build_mandate_name(geography: str, industry: str, mandate_type: str) -> str:
    """Build a clean, reviewable mandate name."""
    suffixes = {
        "buy-side acquisition target list": "Acquisition Targets",
        "investor outreach list": "Investor Outreach",
        "strategic buyer list": "Strategic Buyers",
        "general lead list": "Lead List",
    }
    descriptors = [
        value
        for value in (geography, _display_industry(industry))
        if value.lower() != "unknown"
    ]
    return " ".join(descriptors + [suffixes[mandate_type]]) or "Unknown Lead List"


def parse_mandate(raw_prompt: str) -> Mandate:
    """Parse a mandate locally using deterministic rules only."""
    prompt = raw_prompt.strip()
    if not prompt:
        raise ValueError("Mandate prompt cannot be empty.")

    industry = _extract_industry(prompt)
    geography = _extract_geography(prompt)
    mandate_type = _extract_mandate_type(prompt)
    return Mandate(
        mandate_name=_build_mandate_name(geography, industry, mandate_type),
        mandate_type=mandate_type,
        industry=industry,
        geography=geography,
        target_lead_count=_extract_target_lead_count(prompt),
        campaign_goal=_campaign_goal(mandate_type),
        raw_prompt=prompt,
    )
