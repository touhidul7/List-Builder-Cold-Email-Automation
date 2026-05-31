"""Tests for the offline lead-source planner."""

import pytest

from scripts.icp_builder import build_icp
from scripts.mandate_intake import parse_mandate
from scripts.source_planner import SourcePlan, build_source_plan


def _plan(prompt: str) -> SourcePlan:
    mandate = parse_mandate(prompt)
    return build_source_plan(mandate, build_icp(mandate))


def _providers(plan: SourcePlan) -> list[str]:
    return [step.provider for step in plan.source_steps]


def test_ontario_commercial_cleaning_acquisition_plan() -> None:
    plan = _plan(
        "Find 25 acquisition targets for a client who wants to buy "
        "a commercial cleaning company in Ontario."
    )

    assert _providers(plan)[0] == "Turso"
    assert "Apify Google Maps" in _providers(plan)
    assert _providers(plan).index("Hunter") > _providers(plan).index("Apify Google Maps")


def test_toronto_family_office_investor_plan() -> None:
    plan = _plan("Find family offices in Toronto.")

    assert "investor-directory-miner" in _providers(plan)
    assert "Apollo" in _providers(plan)


def test_oakville_gym_investor_plan() -> None:
    plan = _plan("Find investors for an Oakville gym.")

    assert "investor-directory-miner" in _providers(plan)


def test_strategic_buyer_plan() -> None:
    plan = _plan("Find strategic buyers for a commercial cleaning company in Canada.")

    assert "Apollo" in _providers(plan)
    assert "Consulti B2B" in _providers(plan)


@pytest.mark.parametrize(
    "prompt",
    [
        "Find 25 acquisition targets for a client who wants to buy a commercial cleaning company in Ontario.",
        "Find family offices in Toronto.",
        "Find investors for an Oakville gym.",
        "Find strategic buyers for a commercial cleaning company in Canada.",
    ],
)
def test_linkedin_is_blocked_and_paid_steps_require_approval(prompt: str) -> None:
    plan = _plan(prompt)

    assert "LinkedIn" in plan.blocked_sources
    assert all(step.requires_approval for step in plan.source_steps if step.is_paid)
