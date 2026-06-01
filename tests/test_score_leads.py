"""Tests for the deterministic SOP lead scoring engine."""

import pytest

from scripts.score_leads import (
    calculate_company_score,
    get_priority_tier,
    is_blocked_or_low_quality_source,
)


@pytest.mark.parametrize(
    ("score", "expected"),
    [(100, "Tier 1"), (80, "Tier 1"), (79, "Tier 2"), (60, "Tier 2"), (59, "Tier 3"), (40, "Tier 3"), (39, "Reject")],
)
def test_get_priority_tier(score: int, expected: str) -> None:
    assert get_priority_tier(score) == expected


def test_valid_email_increases_email_quality() -> None:
    breakdown = calculate_company_score(
        {"id": "company-1", "company_name": "Example Cleaning", "industry": "cleaning"},
        [{"email": "owner@example.test", "email_status": "valid"}],
        {"industry": "cleaning", "geography": "unknown"},
    )

    assert breakdown.email_quality == 10


@pytest.mark.parametrize("source", ["LinkedIn", "https://example.test/directory/listings", "Yelp"])
def test_blocked_directory_source_is_detected(source: str) -> None:
    assert is_blocked_or_low_quality_source(source)


def test_strong_local_company_scores_at_least_60() -> None:
    breakdown = calculate_company_score(
        {
            "id": "company-2",
            "company_name": "Clearview Facility Cleaning",
            "industry": "commercial cleaning",
            "website": "https://clearview.example",
            "root_domain": "clearview.example",
            "phone": "+1-416-555-0101",
            "city": "Toronto",
            "province": "Ontario",
            "country": "Canada",
            "source": "google_maps",
            "source_url": "https://maps.example/clearview",
        },
        [
            {
                "full_name": "Maya Patel",
                "title": "Owner",
                "email": "maya@clearview.example",
                "email_status": "valid",
            }
        ],
        {
            "mandate_type": "buy-side acquisition target list",
            "industry": "commercial cleaning",
            "geography": "Ontario",
        },
    )

    assert breakdown.total_score >= 60


def test_total_equals_component_sum_and_is_capped() -> None:
    breakdown = calculate_company_score(
        {
            "id": "company-3",
            "company_name": "Regional HVAC Services",
            "industry": "HVAC",
            "website": "https://hvac.example",
            "phone": "+1-416-555-0102",
            "province": "Ontario",
            "country": "Canada",
            "source": "apollo",
            "source_url": "https://apollo.example/hvac",
        },
        [{"full_name": "Ava Chen", "title": "CEO", "email": "ava@hvac.example", "email_status": "valid"}],
        {"mandate_type": "buy-side acquisition target list", "industry": "HVAC", "geography": "Ontario"},
    )

    component_total = (
        breakdown.icp_fit
        + breakdown.geography_fit
        + breakdown.company_size_fit
        + breakdown.contact_quality
        + breakdown.email_quality
        + breakdown.source_confidence
        + breakdown.strategic_relevance
    )
    assert breakdown.total_score == component_total
    assert breakdown.total_score <= 100
