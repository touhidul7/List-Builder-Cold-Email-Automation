"""Offline, rule-based ICP profile generation."""

from collections.abc import Iterable

from pydantic import BaseModel, Field

from scripts.mandate_intake import Mandate


class ICPProfile(BaseModel):
    """Reviewable ideal customer profile derived from a mandate."""

    primary_icp: str
    secondary_icps: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    target_titles: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    geography_filters: list[str] = Field(default_factory=list)
    company_size_guidance: str | None = None
    positive_signals: list[str] = Field(default_factory=list)
    negative_signals: list[str] = Field(default_factory=list)
    notes: str | None = None


_BUY_SIDE = {
    "primary_icp": (
        "Owner-operated businesses in the target industry and geography that may be "
        "suitable acquisition targets."
    ),
    "target_titles": ["Owner", "Founder", "President", "CEO", "Managing Partner"],
    "positive_signals": [
        "independent business",
        "local or regional operator",
        "established website",
        "clear service offering",
        "phone number available",
        "contact email available",
        "about/team/contact page exists",
    ],
    "negative_signals": [
        "franchise",
        "national chain",
        "directory/listing website",
        "job board",
        "article/blog result",
        "marketplace profile",
        "irrelevant industry",
    ],
    "exclusions": [
        "franchises",
        "national chains",
        "directories",
        "job boards",
        "news articles",
        "marketplaces",
    ],
}

_INVESTOR = {
    "primary_icp": (
        "Investors, family offices, private capital groups, angel investors, or "
        "local business investors relevant to the target industry and geography."
    ),
    "target_titles": [
        "Founder",
        "Managing Partner",
        "Partner",
        "Principal",
        "Investor",
        "President",
        "CEO",
    ],
    "positive_signals": [
        "investor type matches mandate",
        "geography relevance",
        "industry relevance",
        "has firm website",
        "credible source page",
        "contact email available",
        "decision-maker identified",
    ],
    "negative_signals": [
        "generic directory with no firm website",
        "irrelevant investor focus",
        "no geography relevance",
        "no contact path",
        "duplicate investor profile",
    ],
    "exclusions": [
        "generic directories",
        "irrelevant investor lists",
        "inactive firms",
        "no contact path",
    ],
}

_STRATEGIC_BUYER = {
    "primary_icp": "Companies or executives that may be strategic buyers for the target industry.",
    "target_titles": [
        "CEO",
        "President",
        "Founder",
        "Head of Corporate Development",
        "VP Corporate Development",
        "Managing Director",
    ],
    "positive_signals": [
        "industry relevance",
        "strategic fit",
        "established website",
        "decision-maker identified",
        "contact email available",
    ],
    "negative_signals": [
        "irrelevant industry",
        "no strategic fit",
        "directory/listing website",
        "no contact path",
    ],
    "exclusions": ["directories", "irrelevant companies", "no contact path"],
}

_GENERAL = {
    "primary_icp": (
        "B2B companies and decision-makers relevant to the target industry and "
        "geography."
    ),
    "target_titles": ["Owner", "Founder", "President", "CEO", "Operations Manager"],
    "positive_signals": [
        "industry relevance",
        "geography relevance",
        "established website",
        "contact email available",
        "decision-maker identified",
    ],
    "negative_signals": [
        "irrelevant industry",
        "directory/listing website",
        "no contact path",
    ],
    "exclusions": ["directories", "job boards", "news articles", "marketplaces"],
}

_TYPE_RULES = {
    "buy-side acquisition target list": _BUY_SIDE,
    "investor outreach list": _INVESTOR,
    "strategic buyer list": _STRATEGIC_BUYER,
    "general lead list": _GENERAL,
}

_INDUSTRY_RULES = {
    "commercial cleaning": {
        "keywords": [
            "commercial cleaning",
            "janitorial",
            "office cleaning",
            "facility cleaning",
            "building services",
        ],
        "exclusions": ["residential-only cleaners", "maid service only"],
    },
    "gym": {
        "keywords": ["gym", "fitness club", "health club", "wellness", "fitness investor"]
    },
    "family office": {
        "keywords": [
            "family office",
            "private capital",
            "investment firm",
            "wealth management",
            "private investor",
        ]
    },
    "private equity": {
        "keywords": [
            "private equity",
            "investment firm",
            "lower middle market",
            "private capital",
        ]
    },
    "private equity firm": {
        "keywords": [
            "private equity",
            "investment firm",
            "lower middle market",
            "private capital",
        ]
    },
    "HVAC": {
        "keywords": [
            "HVAC",
            "heating and cooling",
            "air conditioning",
            "mechanical contractor",
        ]
    },
    "roofing": {"keywords": ["roofing", "roof contractor", "commercial roofing"]},
    "dental clinic": {"keywords": ["dental clinic", "dentist", "dental practice"]},
    "law firm": {"keywords": ["law firm", "legal services", "attorney"]},
}

_GEOGRAPHY_FILTERS = {
    "Ontario": ["Ontario", "ON", "Canada"],
    "Toronto": ["Toronto", "GTA", "Ontario", "Canada"],
    "Oakville": ["Oakville", "GTA", "Ontario", "Canada"],
    "unknown": ["unknown"],
}


def _merge_unique(*groups: Iterable[str]) -> list[str]:
    """Merge strings without duplicates while preserving their first position."""
    merged: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for item in group:
            if item not in seen:
                seen.add(item)
                merged.append(item)
    return merged


def _geography_filters(geography: str) -> list[str]:
    """Return expanded search filters for known local geographies."""
    return _GEOGRAPHY_FILTERS.get(geography, [geography])


def build_icp(mandate: Mandate) -> ICPProfile:
    """Build a deterministic ICP profile without calling external services."""
    type_rules = _TYPE_RULES.get(mandate.mandate_type, _GENERAL)
    industry_rules = _INDUSTRY_RULES.get(mandate.industry, {})
    return ICPProfile(
        primary_icp=type_rules["primary_icp"],
        secondary_icps=[],
        exclusions=_merge_unique(
            mandate.exclusions,
            type_rules["exclusions"],
            industry_rules.get("exclusions", []),
        ),
        target_titles=_merge_unique(mandate.target_titles, type_rules["target_titles"]),
        keywords=_merge_unique(industry_rules.get("keywords", [mandate.industry])),
        geography_filters=_geography_filters(mandate.geography),
        company_size_guidance=mandate.company_size,
        positive_signals=type_rules["positive_signals"],
        negative_signals=type_rules["negative_signals"],
        notes="Offline rule-based ICP profile. Review before using lead-source integrations.",
    )
