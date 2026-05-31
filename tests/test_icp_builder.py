"""Tests for the offline ICP builder."""

from scripts.icp_builder import build_icp
from scripts.mandate_intake import parse_mandate


def test_commercial_cleaning_acquisition_icp() -> None:
    profile = build_icp(
        parse_mandate(
            "Find 25 acquisition targets for a client who wants to buy "
            "a commercial cleaning company in Ontario."
        )
    )

    assert "Owner-operated businesses" in profile.primary_icp
    assert profile.target_titles
    assert "commercial cleaning" in profile.keywords
    assert "franchises" in profile.exclusions
    assert "residential-only cleaners" in profile.exclusions
    assert profile.geography_filters == ["Ontario", "ON", "Canada"]


def test_family_office_investor_icp() -> None:
    profile = build_icp(parse_mandate("Find family offices in Toronto."))

    assert "Investors, family offices" in profile.primary_icp
    assert profile.target_titles
    assert "family office" in profile.keywords
    assert "generic directories" in profile.exclusions
    assert profile.geography_filters == ["Toronto", "GTA", "Ontario", "Canada"]


def test_oakville_gym_investor_icp() -> None:
    profile = build_icp(parse_mandate("Find investors for an Oakville gym."))

    assert "local business investors" in profile.primary_icp
    assert profile.target_titles
    assert "fitness investor" in profile.keywords
    assert "no contact path" in profile.exclusions
    assert profile.geography_filters == ["Oakville", "GTA", "Ontario", "Canada"]


def test_generic_fallback_icp() -> None:
    profile = build_icp(parse_mandate("Create a prospecting list."))

    assert "B2B companies and decision-makers" in profile.primary_icp
    assert profile.target_titles
    assert profile.keywords == ["unknown"]
    assert "directories" in profile.exclusions
    assert profile.geography_filters == ["unknown"]
