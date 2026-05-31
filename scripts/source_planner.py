"""Offline, rule-based lead-source planning."""

from pydantic import BaseModel, Field

from scripts.icp_builder import ICPProfile
from scripts.mandate_intake import Mandate


class SourceStep(BaseModel):
    """One recommended source action. This model does not execute providers."""

    step_order: int
    provider: str
    source_type: str
    action: str
    reason: str
    is_paid: bool
    requires_approval: bool
    estimated_cost: float | None = None
    expected_output: str
    fallback_provider: str | None = None
    notes: str | None = None


class SourcePlan(BaseModel):
    """Reviewable source plan created without running external integrations."""

    mandate_name: str
    recommended_strategy: str
    source_steps: list[SourceStep]
    duplicate_check_required: bool = True
    cost_approval_required: bool = True
    warnings: list[str] = Field(default_factory=list)
    blocked_sources: list[str] = Field(default_factory=lambda: ["LinkedIn"])


_WARNINGS = [
    "No paid action should run without approval.",
    "Hunter should only be used for missing emails on high-fit leads.",
    "Smartlead campaigns must be created in paused mode.",
    "LinkedIn is not allowed for this system.",
]

_CANADIAN_LOCATIONS = {
    "canada",
    "ontario",
    "on",
    "toronto",
    "gta",
    "oakville",
    "alberta",
    "british columbia",
    "manitoba",
    "new brunswick",
    "newfoundland and labrador",
    "nova scotia",
    "prince edward island",
    "quebec",
    "saskatchewan",
}

_US_LOCATIONS = {
    "united states",
    "usa",
    "u.s.",
    "new york",
    "california",
    "texas",
    "florida",
}

_B2B_INDUSTRIES = {
    "saas",
    "agency",
    "software",
    "technology",
    "private equity",
    "private equity firm",
    "investment firm",
}


def _step(
    provider: str,
    source_type: str,
    action: str,
    reason: str,
    expected_output: str,
    *,
    estimated_cost: float | None = None,
    is_paid: bool | None = None,
    fallback_provider: str | None = None,
    notes: str | None = None,
) -> SourceStep:
    """Create a source step with approval required for every paid action."""
    paid = is_paid if is_paid is not None else estimated_cost is not None
    return SourceStep(
        step_order=0,
        provider=provider,
        source_type=source_type,
        action=action,
        reason=reason,
        is_paid=paid,
        requires_approval=paid,
        estimated_cost=estimated_cost,
        expected_output=expected_output,
        fallback_provider=fallback_provider,
        notes=notes,
    )


def _existing_turso_check() -> SourceStep:
    """Return the mandatory first local duplicate-check step."""
    return _step(
        provider="Turso",
        source_type="existing lead check",
        action="Check stored company and contact fingerprints before paid sourcing.",
        reason="Avoid duplicate records and unnecessary provider spend.",
        expected_output="Known leads and duplicate fingerprints to exclude from later steps.",
        notes="Local database check only. Do not connect to remote Turso yet.",
    )


def _investor_steps() -> list[SourceStep]:
    return [
        _existing_turso_check(),
        _step(
            "investor-directory-miner",
            "investor directory research",
            "Run a small approved test across permitted Google search results, directories, and articles.",
            "Discover relevant investor firms before purchasing broader contact data.",
            "Investor firm candidates with source URLs.",
            estimated_cost=3.00,
            fallback_provider="Consulti B2B",
        ),
        _step(
            "Apollo",
            "investor contact export",
            "Export a small approved batch of investor and professional contacts.",
            "Identify decision-makers at high-fit investor firms.",
            "Professional investor contacts for deduplication and review.",
            estimated_cost=10.00,
            fallback_provider="Consulti B2B",
        ),
        _step(
            "Consulti B2B",
            "B2B contact pull",
            "Pull a small approved B2B enrichment batch for unresolved investor firms.",
            "Fill gaps after directory research and Apollo.",
            "Additional investor firm and decision-maker records.",
            estimated_cost=10.00,
            fallback_provider="Apify leads-finder",
        ),
        _step(
            "Apify leads-finder",
            "B2B lead discovery",
            "Run a small approved leads-finder test for remaining gaps.",
            "Provide a final discovery fallback after higher-confidence sources.",
            "Additional investor leads requiring deduplication.",
            estimated_cost=5.00,
        ),
        _step(
            "Consulti/MillionVerifier",
            "email verification",
            "Verify selected contact emails later, after fit review and deduplication.",
            "Avoid verification spend on weak or duplicate leads.",
            "Verification statuses for approved high-fit contacts.",
            is_paid=True,
            notes="Estimate verification cost before execution and request approval.",
        ),
    ]


def _strategic_buyer_steps() -> list[SourceStep]:
    return [
        _existing_turso_check(),
        _step(
            "Apollo",
            "strategic buyer contact export",
            "Export a small approved batch of strategic-buyer contacts.",
            "Start with professional contacts at likely acquirers.",
            "Strategic-buyer companies and decision-makers.",
            estimated_cost=10.00,
            fallback_provider="Consulti B2B",
        ),
        _step(
            "Consulti B2B",
            "B2B company and contact pull",
            "Pull an approved B2B batch for unresolved strategic buyers.",
            "Broaden coverage after the initial Apollo test.",
            "Additional strategic-buyer companies and contacts.",
            estimated_cost=10.00,
            fallback_provider="Apify leads-finder",
        ),
        _step(
            "Apify leads-finder",
            "B2B lead discovery",
            "Run a small approved leads-finder test for remaining gaps.",
            "Use as a final discovery fallback.",
            "Additional strategic-buyer leads requiring review.",
            estimated_cost=5.00,
        ),
    ]


def _canadian_local_steps() -> list[SourceStep]:
    return [
        _existing_turso_check(),
        _step(
            "Apify Google Maps",
            "local business scrape",
            "Run a small approved Google Maps scraper test.",
            "Maps is a practical first source for Canadian local businesses.",
            "Local business records with websites, phones, and source URLs.",
            estimated_cost=3.00,
            fallback_provider="Consulti local business database",
            notes="Prefer a small test run before expanding volume.",
        ),
        _step(
            "Hunter",
            "email enrichment",
            "Enrich missing emails only for high-fit Google Maps leads with websites.",
            "Limit enrichment spend to promising records with usable domains.",
            "Business-contact email candidates for high-fit leads.",
            estimated_cost=5.00,
            fallback_provider="Consulti",
        ),
        _step(
            "Consulti",
            "local business enrichment",
            "Pull extra enrichment only where high-fit records still have data gaps.",
            "Use as a later enrichment layer instead of the first paid source.",
            "Additional company and contact details for unresolved leads.",
            estimated_cost=10.00,
        ),
    ]


def _us_local_steps() -> list[SourceStep]:
    return [
        _existing_turso_check(),
        _step(
            "Consulti local business database",
            "local business database",
            "Pull a small approved U.S. local-business test batch.",
            "Use Consulti first for U.S. local-business coverage.",
            "Local business records for deduplication and fit review.",
            estimated_cost=10.00,
            fallback_provider="Apify Google Maps",
        ),
        _step(
            "Apify Google Maps",
            "local business scrape",
            "Run a small approved Maps backup scrape for coverage gaps.",
            "Supplement missing local-business records.",
            "Additional local business records with source URLs.",
            estimated_cost=3.00,
        ),
        _step(
            "Hunter",
            "email enrichment",
            "Enrich missing website emails only for strong-fit leads.",
            "Avoid enrichment spend on records without a website or fit signal.",
            "Business-contact email candidates for selected leads.",
            estimated_cost=5.00,
        ),
    ]


def _b2b_steps() -> list[SourceStep]:
    return [
        _existing_turso_check(),
        _step(
            "Consulti B2B",
            "B2B company and contact pull",
            "Pull a small approved B2B test batch.",
            "Start with structured B2B records for the target profile.",
            "B2B company and decision-maker records.",
            estimated_cost=10.00,
            fallback_provider="Apify leads-finder",
        ),
        _step(
            "Apify leads-finder",
            "B2B lead discovery",
            "Run a small approved leads-finder test for coverage gaps.",
            "Supplement structured B2B results.",
            "Additional B2B leads requiring deduplication.",
            estimated_cost=5.00,
        ),
        _step(
            "Hunter",
            "email enrichment",
            "Enrich only strong-fit leads with a domain and missing email.",
            "Control enrichment cost and preserve lead quality.",
            "Business-contact email candidates for selected leads.",
            estimated_cost=5.00,
        ),
    ]


def _has_location(icp: ICPProfile, locations: set[str]) -> bool:
    """Return whether expanded ICP geography filters include a location group."""
    return any(value.lower() in locations for value in icp.geography_filters)


def _number_steps(steps: list[SourceStep]) -> list[SourceStep]:
    """Assign stable one-based execution order after a template is selected."""
    return [
        step.model_copy(update={"step_order": index})
        for index, step in enumerate(steps, start=1)
    ]


def build_source_plan(mandate: Mandate, icp: ICPProfile) -> SourcePlan:
    """Create a source recommendation without running any external provider."""
    if mandate.mandate_type == "investor outreach list":
        strategy = (
            "Start with the existing-lead check, then test investor-directory "
            "research before paid professional-contact sources and later verification."
        )
        steps = _investor_steps()
    elif mandate.mandate_type == "strategic buyer list":
        strategy = (
            "Start with the existing-lead check, then test Apollo for strategic-buyer "
            "contacts before expanding through Consulti B2B and Apify leads-finder."
        )
        steps = _strategic_buyer_steps()
    elif _has_location(icp, _CANADIAN_LOCATIONS) and mandate.mandate_type in {
        "buy-side acquisition target list",
        "general lead list",
    }:
        strategy = (
            "Start with the existing-lead check, then test Google Maps for Canadian "
            "local-business coverage before targeted email and data enrichment."
        )
        steps = _canadian_local_steps()
    elif _has_location(icp, _US_LOCATIONS):
        strategy = (
            "Start with the existing-lead check, then test Consulti local-business "
            "coverage before using Maps and targeted email enrichment as fallbacks."
        )
        steps = _us_local_steps()
    elif mandate.mandate_type == "general lead list" or mandate.industry.lower() in {
        industry.lower() for industry in _B2B_INDUSTRIES
    }:
        strategy = (
            "Start with the existing-lead check, then test structured B2B sources "
            "before enriching only strong-fit records with missing emails."
        )
        steps = _b2b_steps()
    else:
        strategy = (
            "Start with the existing-lead check, then use a small structured B2B "
            "test before expanding source coverage."
        )
        steps = _b2b_steps()

    return SourcePlan(
        mandate_name=mandate.mandate_name,
        recommended_strategy=strategy,
        source_steps=_number_steps(steps),
        warnings=_WARNINGS,
    )
