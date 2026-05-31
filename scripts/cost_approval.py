"""Local-only cost approval requests and audit records."""

import json
from typing import Literal
import uuid

from pydantic import BaseModel

from scripts.db import get_connection


class CostApprovalRequest(BaseModel):
    """A proposed paid action that requires a recorded human decision."""

    mandate_id: str | None = None
    action_type: str
    action_description: str
    provider: str
    reason: str
    estimated_cost: float
    estimated_credits: int | None = None
    expected_output: str
    alternatives: str | None = None
    risk: str | None = None


class CostApprovalResult(BaseModel):
    """The locally recorded outcome of an approval request."""

    approved: bool
    approval_status: str
    approved_by: str | None = None
    approval_message: str
    cost_approval_id: str | None = None


_APPROVAL_TEXT = {"yes", "y", "approved", "approve", "go ahead", "confirmed", "confirm"}
_REJECTION_TEXT = {"no", "n", "stop", "reject", "rejected", "do not proceed", "cancel"}
_APPROVAL_STATUSES = {"pending", "approved", "rejected"}


def format_cost_approval_message(request: CostApprovalRequest) -> str:
    """Format the exact review message shown before any paid action."""
    estimated_credits = (
        str(request.estimated_credits)
        if request.estimated_credits is not None
        else "N/A"
    )
    alternatives = request.alternatives or "No cheaper alternative available."
    risk = (
        request.risk
        or "Results may include duplicates, irrelevant records, or missing emails."
    )
    return (
        "Cost Approval Required\n\n"
        "Action:\n"
        f"{request.action_description}\n\n"
        "Reason:\n"
        f"{request.reason}\n\n"
        "Estimated Cost:\n"
        f"${request.estimated_cost:.2f}\n\n"
        "Estimated Credits:\n"
        f"{estimated_credits}\n\n"
        "Expected Output:\n"
        f"{request.expected_output}\n\n"
        "Alternatives:\n"
        f"{alternatives}\n\n"
        "Risk:\n"
        f"{risk}\n\n"
        "Do you approve this cost?\n"
        "Reply YES to approve or NO to stop."
    )


def is_approval_text(text: str) -> bool:
    """Return whether text is an explicit approval response."""
    return text.strip().lower() in _APPROVAL_TEXT


def is_rejection_text(text: str) -> bool:
    """Return whether text is an explicit rejection response."""
    return text.strip().lower() in _REJECTION_TEXT


def record_cost_approval(
    request: CostApprovalRequest,
    approval_status: Literal["pending", "approved", "rejected"] | str,
    approved_by: str | None = None,
) -> str:
    """Insert one cost-approval audit record into local SQLite."""
    if approval_status not in _APPROVAL_STATUSES:
        raise ValueError(f"Invalid approval status: {approval_status!r}")

    cost_approval_id = str(uuid.uuid4())
    notes = json.dumps(
        {
            "reason": request.reason,
            "expected_output": request.expected_output,
            "alternatives": request.alternatives,
            "risk": request.risk,
        },
        sort_keys=True,
    )
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO cost_approvals (
                id,
                mandate_id,
                action_type,
                action_description,
                provider,
                estimated_cost,
                actual_cost,
                estimated_credits,
                approval_status,
                approved_by,
                approved_at,
                notes
            ) VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, CASE WHEN ? = 'approved'
                THEN CURRENT_TIMESTAMP ELSE NULL END, ?)
            """,
            (
                cost_approval_id,
                request.mandate_id,
                request.action_type,
                request.action_description,
                request.provider,
                request.estimated_cost,
                request.estimated_credits,
                approval_status,
                approved_by,
                approval_status,
                notes,
            ),
        )
        connection.commit()
    return cost_approval_id


def process_cost_approval(
    request: CostApprovalRequest,
    response_text: str | None = None,
    approved_by: str | None = None,
) -> CostApprovalResult:
    """Classify a response and persist its local approval audit record."""
    response = response_text or ""
    if is_approval_text(response):
        approval_status = "approved"
        approved = True
    elif is_rejection_text(response):
        approval_status = "rejected"
        approved = False
    else:
        approval_status = "pending"
        approved = False

    cost_approval_id = record_cost_approval(request, approval_status, approved_by)
    return CostApprovalResult(
        approved=approved,
        approval_status=approval_status,
        approved_by=approved_by,
        approval_message=format_cost_approval_message(request),
        cost_approval_id=cost_approval_id,
    )
