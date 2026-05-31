"""Tests for local-only cost approval request handling."""

import pytest

from scripts.cost_approval import (
    CostApprovalRequest,
    format_cost_approval_message,
    is_approval_text,
    is_rejection_text,
    process_cost_approval,
)


@pytest.fixture
def approval_request() -> CostApprovalRequest:
    return CostApprovalRequest(
        action_type="scrape",
        action_description="Run an approved small scraper test",
        provider="apify",
        reason="Need local business leads",
        estimated_cost=3,
        expected_output="25-100 local company records",
    )


def test_format_cost_approval_message_includes_required_sections(
    approval_request: CostApprovalRequest,
) -> None:
    message = format_cost_approval_message(approval_request)

    assert message.startswith("Cost Approval Required\n\n")
    for section in (
        "Action:",
        "Reason:",
        "Estimated Cost:",
        "Estimated Credits:",
        "Expected Output:",
        "Alternatives:",
        "Risk:",
        "Do you approve this cost?",
        "Reply YES to approve or NO to stop.",
    ):
        assert section in message
    assert "$3.00" in message
    assert "N/A" in message
    assert "No cheaper alternative available." in message


@pytest.mark.parametrize("text", ["yes", "YES", "approved", "go ahead"])
def test_approval_text_is_accepted(text: str) -> None:
    assert is_approval_text(text)


@pytest.mark.parametrize("text", ["no", "NO", "stop", "cancel"])
def test_rejection_text_is_accepted(text: str) -> None:
    assert is_rejection_text(text)


def test_unknown_response_is_not_approval_or_rejection() -> None:
    assert not is_approval_text("maybe")
    assert not is_rejection_text("maybe")


def test_unknown_response_becomes_pending(
    approval_request: CostApprovalRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "scripts.cost_approval.record_cost_approval",
        lambda *_args, **_kwargs: "local-test-id",
    )

    result = process_cost_approval(approval_request, "maybe")

    assert not result.approved
    assert result.approval_status == "pending"
    assert result.cost_approval_id == "local-test-id"
