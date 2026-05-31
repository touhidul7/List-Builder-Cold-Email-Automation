"""Tests for the offline mandate intake parser."""

from scripts.mandate_intake import parse_mandate


def test_commercial_cleaning_acquisition_in_ontario() -> None:
    mandate = parse_mandate(
        "Find 25 acquisition targets for a client who wants to buy "
        "a commercial cleaning company in Ontario."
    )

    assert mandate.mandate_name == "Ontario Commercial Cleaning Acquisition Targets"
    assert mandate.mandate_type == "buy-side acquisition target list"
    assert mandate.industry == "commercial cleaning"
    assert mandate.geography == "Ontario"
    assert mandate.target_lead_count == 25
    assert mandate.campaign_goal == "book acquisition conversation"


def test_family_office_investors_in_toronto() -> None:
    mandate = parse_mandate("Find family offices in Toronto.")

    assert mandate.mandate_name == "Toronto Family Office Investor Outreach"
    assert mandate.mandate_type == "investor outreach list"
    assert mandate.industry == "family office"
    assert mandate.geography == "Toronto"
    assert mandate.target_lead_count == 25
    assert mandate.campaign_goal == "book investor conversation"


def test_gym_investors_in_oakville() -> None:
    mandate = parse_mandate("Find investors for an Oakville gym.")

    assert mandate.mandate_name == "Oakville Gym Investor Outreach"
    assert mandate.mandate_type == "investor outreach list"
    assert mandate.industry == "gym"
    assert mandate.geography == "Oakville"
    assert mandate.target_lead_count == 25
    assert mandate.campaign_goal == "book investor conversation"


def test_generic_lead_list_fallback() -> None:
    mandate = parse_mandate("Create a prospecting list.")

    assert mandate.mandate_name == "Lead List"
    assert mandate.mandate_type == "general lead list"
    assert mandate.industry == "unknown"
    assert mandate.geography == "unknown"
    assert mandate.target_lead_count == 25
    assert mandate.campaign_goal == "book intro call"
