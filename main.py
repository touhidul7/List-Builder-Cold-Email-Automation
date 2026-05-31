"""CLI entry point for ListBuilder + ColdEmail AI."""

import inspect

import click
import typer
from rich.console import Console
from rich.table import Table
from typer.core import TyperOption

from scripts.config import get_settings
from scripts.cost_approval import CostApprovalRequest, process_cost_approval
from scripts.check_existing_leads import check_existing_leads
from scripts.db import count_rows, get_connection, get_local_db_path
from scripts.icp_builder import build_icp
from scripts.mandate_intake import parse_mandate
from scripts.mandate_store import list_mandates, save_mandate
from scripts.source_planner import build_source_plan


def _apply_typer_click_compatibility() -> None:
    """Bridge Typer 0.12 value options and help rendering on Click 8.3."""
    original_option_init = TyperOption.__init__

    def option_init(self: TyperOption, *args: object, **kwargs: object) -> None:
        if kwargs.get("is_flag") is None and kwargs.get("flag_value") is None:
            kwargs["is_flag"] = False
        original_option_init(self, *args, **kwargs)

    TyperOption.__init__ = option_init  # type: ignore[method-assign]

    make_metavar = click.Parameter.make_metavar
    if inspect.signature(make_metavar).parameters["ctx"].default is inspect.Parameter.empty:

        def make_metavar_with_optional_ctx(
            self: click.Parameter, ctx: click.Context | None = None
        ) -> str:
            return make_metavar(self, ctx)

        click.Parameter.make_metavar = make_metavar_with_optional_ctx  # type: ignore[method-assign]


_apply_typer_click_compatibility()

app = typer.Typer(
    help="Safe CLI automation for list building and paused cold-email deployment.",
    invoke_without_command=True,
)
console = Console()


def _configured(*values: str) -> str:
    """Return a display status for integration credentials."""
    return "[green]configured[/green]" if all(values) else "[yellow]missing[/yellow]"


@app.command()
def status() -> None:
    """Show local configuration status without calling external services."""
    settings = get_settings()
    console.print("[bold]ListBuilder + ColdEmail AI[/bold]")
    console.print(f"Environment: {settings.app_env}")
    console.print(f"Dry run mode: {settings.dry_run}")
    console.print(f"Budget cap: {settings.default_budget_cap:g}")

    integrations = {
        "Anthropic": _configured(settings.anthropic_api_key),
        "Apify": _configured(settings.apify_api_token),
        "Apollo": _configured(settings.apollo_api_key),
        "Consulti": _configured(settings.consulti_api_key),
        "Hunter": _configured(settings.hunter_api_key),
        "MillionVerifier": _configured(settings.millionverifier_api_key),
        "Turso": _configured(settings.turso_database_url, settings.turso_auth_token),
        "Smartlead": _configured(settings.smartlead_api_key),
        "Winnr": _configured(settings.winnr_api_key, settings.winnr_account_email),
    }
    table = Table(title="Integrations")
    table.add_column("Integration")
    table.add_column("Status")
    for name, integration_status in integrations.items():
        table.add_row(name, integration_status)
    console.print(table)


@app.command()
def plan() -> None:
    """Print the planned automation phases."""
    phases = [
        "Mandate intake",
        "ICP builder",
        "Source planner",
        "Existing lead check",
        "Cost approval gate",
        "Lead source integrations",
        "Enrichment",
        "Verification",
        "Scoring",
        "Research",
        "Cold email copy",
        "Smartlead paused deploy",
        "Reporting",
    ]
    console.print("[bold]Build phases[/bold]")
    for index, phase in enumerate(phases, start=1):
        console.print(f"{index}. {phase}")


@app.command("db-status")
def db_status() -> None:
    """Show local SQLite row counts without connecting to Turso."""
    db_path = get_local_db_path()
    if not db_path.exists():
        console.print(
            "Local database not found. Run: python -m scripts.init_db --reset --seed"
        )
        return

    summary_tables = (
        "mandates",
        "companies",
        "contacts",
        "cost_approvals",
        "campaigns",
        "domains",
        "inboxes",
    )
    table = Table(title="Local SQLite Summary")
    table.add_column("Table")
    table.add_column("Rows", justify="right")
    with get_connection(db_path) as connection:
        for table_name in summary_tables:
            table.add_row(table_name, str(count_rows(connection, table_name)))
    console.print(table)


@app.command()
def intake(raw_prompt: str) -> None:
    """Parse a mandate locally using deterministic rules."""
    mandate = parse_mandate(raw_prompt)
    fields = (
        "mandate_name",
        "mandate_type",
        "industry",
        "geography",
        "target_lead_count",
        "campaign_goal",
        "company_size",
        "target_titles",
        "exclusions",
    )
    table = Table(title="Mandate Intake")
    table.add_column("Field")
    table.add_column("Value")
    data = mandate.model_dump()
    for field in fields:
        table.add_row(field, str(data[field]))
    console.print(table)


@app.command()
def icp(raw_prompt: str) -> None:
    """Build an ICP profile locally from a natural-language mandate."""
    profile = build_icp(parse_mandate(raw_prompt))
    fields = (
        ("Primary ICP", "primary_icp"),
        ("Secondary ICPs", "secondary_icps"),
        ("Target Titles", "target_titles"),
        ("Keywords", "keywords"),
        ("Geography Filters", "geography_filters"),
        ("Exclusions", "exclusions"),
        ("Positive Signals", "positive_signals"),
        ("Negative Signals", "negative_signals"),
    )
    table = Table(title="ICP Profile")
    table.add_column("Field")
    table.add_column("Value")
    data = profile.model_dump()
    for label, field in fields:
        table.add_row(label, str(data[field]))
    console.print(table)


@app.command("source-plan")
def source_plan(raw_prompt: str) -> None:
    """Build a review-only lead-source plan without running integrations."""
    mandate = parse_mandate(raw_prompt)
    plan = build_source_plan(mandate, build_icp(mandate))
    console.print("[bold]Recommended strategy[/bold]")
    console.print(plan.recommended_strategy)

    table = Table(title="Source Steps")
    for column in (
        "Order",
        "Provider",
        "Source Type",
        "Action",
        "Paid",
        "Approval",
        "Est. Cost",
        "Expected Output",
    ):
        table.add_column(column)
    for step in plan.source_steps:
        estimated_cost = (
            f"${step.estimated_cost:.2f}" if step.estimated_cost is not None else "-"
        )
        table.add_row(
            str(step.step_order),
            step.provider,
            step.source_type,
            step.action,
            str(step.is_paid),
            str(step.requires_approval),
            estimated_cost,
            step.expected_output,
        )
    console.print(table)
    console.print("[bold]Warnings[/bold]")
    for warning in plan.warnings:
        console.print(f"- {warning}")
    console.print(f"[bold]Blocked sources[/bold]: {', '.join(plan.blocked_sources)}")


@app.command("cost-approval")
def cost_approval(
    provider: str = typer.Option(
        ..., is_flag=False, help="Provider for the proposed paid action."
    ),
    action_type: str = typer.Option(
        ..., is_flag=False, help="Type of proposed paid action."
    ),
    estimated_cost: float = typer.Option(
        ..., is_flag=False, help="Estimated cost in USD."
    ),
    description: str = typer.Option(
        ..., is_flag=False, help="Description of the proposed action."
    ),
    reason: str = typer.Option(..., is_flag=False, help="Reason the action is needed."),
    expected_output: str = typer.Option(
        ..., is_flag=False, help="Expected records or enrichment."
    ),
    estimated_credits: int | None = typer.Option(
        None, is_flag=False, help="Estimated provider credits."
    ),
    alternatives: str | None = typer.Option(
        None, is_flag=False, help="Cheaper alternatives considered."
    ),
    risk: str | None = typer.Option(
        None, is_flag=False, help="Known quality or spend risk."
    ),
    response: str | None = typer.Option(
        None, is_flag=False, help="Approval or rejection response."
    ),
    approved_by: str = typer.Option(
        "advisor", is_flag=False, help="Local reviewer name."
    ),
) -> None:
    """Create and record a local-only cost approval request."""
    request = CostApprovalRequest(
        action_type=action_type,
        action_description=description,
        provider=provider,
        reason=reason,
        estimated_cost=estimated_cost,
        estimated_credits=estimated_credits,
        expected_output=expected_output,
        alternatives=alternatives,
        risk=risk,
    )
    result = process_cost_approval(request, response, approved_by)
    console.print(result.approval_message)
    console.print(f"\nApproval status: {result.approval_status}")
    console.print(f"cost_approval_id: {result.cost_approval_id}")


@app.command("save-mandate")
def save_mandate_command(raw_prompt: str) -> None:
    """Parse and persist a mandate in the local SQLite database."""
    mandate = parse_mandate(raw_prompt)
    mandate_id = save_mandate(mandate)
    console.print(f"[bold]mandate_id[/bold]: {mandate_id}")
    table = Table(title="Saved Mandate")
    table.add_column("Field")
    table.add_column("Value")
    for field, value in mandate.model_dump().items():
        table.add_row(field, str(value))
    console.print(table)


@app.command("mandates")
def mandates_command() -> None:
    """Show recently saved local mandates."""
    table = Table(title="Recent Mandates")
    for column in (
        "ID",
        "Mandate Name",
        "Mandate Type",
        "Industry",
        "Geography",
        "Lead Count",
        "Status",
    ):
        table.add_column(column)
    for mandate in list_mandates():
        table.add_row(
            mandate["id"][:8],
            mandate["mandate_name"],
            mandate["mandate_type"],
            mandate["industry"],
            mandate["geography"],
            str(mandate["target_lead_count"]),
            mandate["status"],
        )
    console.print(table)


@app.command("existing-check")
def existing_check(raw_prompt: str) -> None:
    """Check local records before recommending paid lead sources."""
    mandate = parse_mandate(raw_prompt)
    summary = check_existing_leads(mandate.industry, mandate.geography)
    table = Table(title="Existing Lead Check")
    table.add_column("Field")
    table.add_column("Value")
    for field, value in summary.model_dump().items():
        table.add_row(field, str(value))
    console.print(table)


@app.callback()
def main(ctx: typer.Context) -> None:
    """Run the status command when no subcommand is provided."""
    if ctx.invoked_subcommand is None:
        status()


if __name__ == "__main__":
    app()
