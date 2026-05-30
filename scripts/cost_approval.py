"""Human approval gate for future paid provider calls."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CostApproval:
    """Recorded decision for a proposed paid action."""

    provider: str
    estimated_cost: float
    approved: bool = False
    approved_by: str = ""


def require_approval(approval: CostApproval) -> None:
    """Block paid work unless a named human approved it."""
    if not approval.approved or not approval.approved_by.strip():
        raise PermissionError("Paid API usage requires explicit human approval.")

