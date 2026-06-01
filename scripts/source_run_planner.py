"""Local-only source-run planning and pending approval creation."""

import json
import uuid

from pydantic import BaseModel

from scripts.cost_approval import CostApprovalRequest, record_cost_approval
from scripts.db import get_connection
from scripts.icp_builder import build_icp
from scripts.mandate_intake import Mandate
from scripts.mandate_store import get_mandate
from scripts.source_planner import SourceStep, build_source_plan


class PlannedSourceRun(BaseModel):
    """One persisted source-run plan. It never executes the provider."""

    source_run_id: str
    cost_approval_id: str | None = None
    mandate_id: str
    provider: str
    source_type: str
    query: str
    status: str
    estimated_cost: float | None
    requires_approval: bool
    approval_status: str | None = None
    reason: str
    expected_output: str


def find_source_run_by_id_or_prefix(source_run_id_or_prefix: str) -> dict | None:
    """Find one local source run by its full ID or an unambiguous prefix."""
    with get_connection() as connection:
        exact = connection.execute(
            "SELECT * FROM source_runs WHERE id = ?",
            (source_run_id_or_prefix,),
        ).fetchone()
        if exact is not None:
            return dict(exact)
        matches = connection.execute(
            "SELECT * FROM source_runs WHERE id LIKE ? ORDER BY id",
            (f"{source_run_id_or_prefix}%",),
        ).fetchall()
    if len(matches) > 1:
        raise ValueError("Multiple source runs match this prefix. Use the full ID.")
    return dict(matches[0]) if matches else None


def _json_list(value: object) -> list[str]:
    """Load a stored JSON-list field defensively."""
    if not value:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    loaded = json.loads(str(value))
    return [str(item) for item in loaded] if isinstance(loaded, list) else []


def _stored_mandate(mandate_id: str) -> Mandate:
    """Reconstruct a parsed Mandate from its local SQLite record."""
    stored = get_mandate(mandate_id)
    if stored is None:
        raise ValueError(f"Mandate not found: {mandate_id}")
    return Mandate(
        mandate_name=stored["mandate_name"],
        mandate_type=stored["mandate_type"],
        industry=stored["industry"],
        geography=stored["geography"],
        target_lead_count=stored["target_lead_count"],
        campaign_goal=stored["campaign_goal"],
        company_size=stored.get("company_size"),
        target_titles=_json_list(stored.get("target_titles")),
        exclusions=_json_list(stored.get("exclusions")),
        raw_prompt=stored["mandate_name"],
    )


def build_source_query(mandate: Mandate, source_step: SourceStep) -> str:
    """Build a concise provider-specific query from local mandate fields."""
    industry = mandate.industry
    geography = mandate.geography
    provider = source_step.provider.lower()
    if provider == "apify google maps":
        return f"{industry} companies in {geography}"
    if provider == "investor-directory-miner":
        return f"{industry} investors in {geography}"
    if provider == "apollo":
        return f"{industry} investors {geography}"
    if provider == "consulti b2b":
        return f"{industry} {geography}"
    if provider == "hunter":
        return f"missing email enrichment for {industry} {geography}"
    return f"{industry} {geography} {source_step.source_type}"


def create_source_runs_for_mandate(
    mandate_id: str,
    auto_create_approvals: bool = True,
) -> list[PlannedSourceRun]:
    """Persist source-run plans and optional pending approvals without execution."""
    mandate = _stored_mandate(mandate_id)
    source_plan = build_source_plan(mandate, build_icp(mandate))
    planned_runs: list[PlannedSourceRun] = []

    for step in source_plan.source_steps:
        if step.source_type == "existing lead check":
            continue

        source_run_id = str(uuid.uuid4())
        status = "approval_required" if step.is_paid else "planned"
        query = build_source_query(mandate, step)
        cost_approval_id: str | None = None
        approval_status: str | None = None
        if step.is_paid and auto_create_approvals:
            request = CostApprovalRequest(
                mandate_id=mandate_id,
                action_type=step.source_type,
                action_description=step.action,
                provider=step.provider,
                reason=step.reason,
                estimated_cost=step.estimated_cost or 0,
                expected_output=step.expected_output,
                alternatives=(
                    step.fallback_provider
                    or "Use existing records first or run a smaller test."
                ),
                risk="Results may include duplicates, irrelevant records, or missing emails.",
            )
            cost_approval_id = record_cost_approval(request, "pending")
            approval_status = "pending"

        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO source_runs (
                    id,
                    mandate_id,
                    provider,
                    source_type,
                    query,
                    status,
                    estimated_cost,
                    raw_output_path,
                    records_found,
                    records_imported
                ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, 0, 0)
                """,
                (
                    source_run_id,
                    mandate_id,
                    step.provider,
                    step.source_type,
                    query,
                    status,
                    step.estimated_cost,
                ),
            )
            connection.commit()

        planned_runs.append(
            PlannedSourceRun(
                source_run_id=source_run_id,
                cost_approval_id=cost_approval_id,
                mandate_id=mandate_id,
                provider=step.provider,
                source_type=step.source_type,
                query=query,
                status=status,
                estimated_cost=step.estimated_cost,
                requires_approval=step.requires_approval,
                approval_status=approval_status,
                reason=step.reason,
                expected_output=step.expected_output,
            )
        )
    return planned_runs
