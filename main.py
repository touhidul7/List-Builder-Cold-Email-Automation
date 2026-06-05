"""CLI entry point for ListBuilder + ColdEmail AI."""

import inspect

import click
import typer
from rich.console import Console
from rich.table import Table
from typer.core import TyperOption

from scripts.config import get_settings
from scripts.cold_email_copywriting import (
    get_latest_email_sequence,
    save_email_sequence_for_mandate,
)
from scripts.cost_approval import CostApprovalRequest, process_cost_approval
from scripts.check_existing_leads import check_existing_leads
from scripts.db import count_rows, get_connection, get_local_db_path
from scripts.dedupe_leads import (
    dedupe_companies_preview,
    find_duplicate_company,
    update_company_fingerprints,
)
from scripts.icp_builder import build_icp
from scripts.mandate_intake import parse_mandate
from scripts.mandate_store import list_mandates, save_mandate
from scripts.mock_campaign_reporting import generate_mock_campaign_events
from scripts.mock_email_enrichment import enrich_companies_without_contacts
from scripts.mock_email_verification import verify_contacts_mock
from scripts.mock_smartlead_deploy import create_mock_smartlead_campaign
from scripts.production_readiness import get_readiness_items, summarize_readiness
from scripts.research_best_leads import research_tier_one_leads
from scripts.score_leads import (
    get_latest_active_mandate_id,
    score_companies_for_mandate,
)
from scripts.run_apify_google_maps import run_apify_google_maps_mock
from scripts.dry_pipeline import run_dry_pipeline
from scripts.source_planner import build_source_plan
from scripts.source_run_planner import (
    PlannedSourceRun,
    create_source_runs_for_mandate,
    find_source_run_by_id_or_prefix,
)


def _apply_typer_click_compatibility() -> None:
    """Bridge Typer 0.12 value options and help rendering on Click 8.3."""
    original_option_init = TyperOption.__init__

    def option_init(self: TyperOption, *args: object, **kwargs: object) -> None:
        if kwargs.get("is_flag") is None and kwargs.get("flag_value") is None:
            kwargs["is_flag"] = False
        elif kwargs.get("is_flag") is True and kwargs.get("flag_value") is None:
            kwargs["flag_value"] = True
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


@app.command("readiness")
def readiness_command() -> None:
    """Show SOP production-readiness status without calling providers."""
    items = get_readiness_items()
    summary = summarize_readiness(items)
    console.print("[bold]SOP Production Readiness[/bold]")
    console.print(
        "This check is read-only. It does not call providers, spend credits, or send email."
    )
    console.print(
        f"Done: {summary['done']} | Partial: {summary['partial']} | "
        f"Missing: {summary['missing']} | Blocked: {summary['blocked']}"
    )

    table = Table(title="Requirement Checklist")
    table.add_column("Area")
    table.add_column("Status")
    table.add_column("Surfaces")
    table.add_column("Requirement")
    table.add_column("Next Step")
    status_colors = {
        "done": "green",
        "partial": "yellow",
        "missing": "red",
        "blocked": "magenta",
    }
    for item in items:
        table.add_row(
            item.area,
            f"[{status_colors[item.status]}]{item.status}[/{status_colors[item.status]}]",
            ", ".join(item.surfaces),
            item.requirement,
            item.next_step,
        )
    console.print(table)


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
        "source_runs",
        "lead_scores",
        "research_logs",
        "personalization",
        "email_sequences",
        "campaign_leads",
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


@app.command("score-leads")
def score_leads_command(
    mandate_id: str | None = typer.Option(
        None, is_flag=False, help="Stored mandate ID. Defaults to the latest active mandate."
    ),
) -> None:
    """Score local companies and persist SOP score breakdowns."""
    resolved_mandate_id = mandate_id or get_latest_active_mandate_id()
    breakdowns = score_companies_for_mandate(resolved_mandate_id)
    console.print(f"[bold]mandate_id[/bold]: {resolved_mandate_id}")
    console.print(f"[bold]scored_companies[/bold]: {len(breakdowns)}")
    table = Table(title="Lead Scores")
    for column in (
        "Company",
        "Total",
        "Tier",
        "ICP",
        "Geo",
        "Contact",
        "Email",
        "Source",
        "Reason",
    ):
        table.add_column(column)
    for score in breakdowns:
        table.add_row(
            score.company_name,
            str(score.total_score),
            score.priority_tier,
            str(score.icp_fit),
            str(score.geography_fit),
            str(score.contact_quality),
            str(score.email_quality),
            str(score.source_confidence),
            score.score_reason,
        )
    console.print(table)


@app.command("update-fingerprints")
def update_fingerprints_command() -> None:
    """Update local company root domains and stable fingerprints."""
    updated = update_company_fingerprints()
    console.print(f"Updated company fingerprints: {updated}")


@app.command("dedupe-preview")
def dedupe_preview_command() -> None:
    """Show possible local duplicate groups without deleting records."""
    groups = dedupe_companies_preview()
    if not groups:
        console.print("No possible duplicate company groups found.")
        return
    table = Table(title="Possible Duplicate Companies")
    for column in ("Type", "Value", "Company IDs", "Company Names"):
        table.add_column(column)
    for group in groups:
        table.add_row(
            group["duplicate_type"],
            group["value"],
            ", ".join(group["company_ids"]),
            ", ".join(group["company_names"]),
        )
    console.print(table)


@app.command("duplicate-check")
def duplicate_check_command(
    company_name: str | None = typer.Option(None, is_flag=False),
    website: str | None = typer.Option(None, is_flag=False),
    root_domain: str | None = typer.Option(None, is_flag=False),
    city: str | None = typer.Option(None, is_flag=False),
    province: str | None = typer.Option(None, is_flag=False),
    phone: str | None = typer.Option(None, is_flag=False),
    google_place_id: str | None = typer.Option(None, is_flag=False),
    apollo_company_id: str | None = typer.Option(None, is_flag=False),
    consulti_company_id: str | None = typer.Option(None, is_flag=False),
    source_url: str | None = typer.Option(None, is_flag=False),
) -> None:
    """Check a proposed company against local records without creating it."""
    result = find_duplicate_company(
        company_name=company_name,
        website=website,
        root_domain=root_domain,
        city=city,
        province=province,
        phone=phone,
        google_place_id=google_place_id,
        apollo_company_id=apollo_company_id,
        consulti_company_id=consulti_company_id,
        source_url=source_url,
    )
    console.print(f"Duplicate exists: {result.is_duplicate}")
    console.print(f"Recommended action: {result.recommended_action}")
    table = Table(title="Duplicate Matches")
    for column in ("Existing ID", "Type", "Confidence", "Reason"):
        table.add_column(column)
    for match in result.matches:
        table.add_row(
            match.existing_id,
            match.duplicate_type,
            match.confidence,
            match.reason,
        )
    console.print(table)


def _print_planned_source_runs(runs: list[PlannedSourceRun]) -> None:
    """Print persisted source-run plans in a compact table."""
    table = Table(title="Planned Source Runs")
    for column in (
        "Run ID",
        "Provider",
        "Source Type",
        "Query",
        "Status",
        "Est. Cost",
        "Approval",
        "Approval ID",
    ):
        table.add_column(column)
    for run in runs:
        table.add_row(
            run.source_run_id[:8],
            run.provider,
            run.source_type,
            run.query,
            run.status,
            f"${run.estimated_cost:.2f}" if run.estimated_cost is not None else "-",
            run.approval_status or "-",
            run.cost_approval_id[:8] if run.cost_approval_id else "-",
        )
    console.print(table)


@app.command("plan-runs")
def plan_runs_command(
    mandate_id: str,
    no_approvals: bool = typer.Option(
        False,
        "--no-approvals",
        help="Create source runs without pending cost-approval records.",
    ),
) -> None:
    """Persist source-run plans without calling external providers."""
    runs = create_source_runs_for_mandate(
        mandate_id,
        auto_create_approvals=not no_approvals,
    )
    _print_planned_source_runs(runs)
    console.print("No external APIs were called. These are planned runs only.")


@app.command("create-mandate-plan")
def create_mandate_plan_command(raw_prompt: str) -> None:
    """Persist a mandate, inspect local leads, and create source-run plans."""
    mandate = parse_mandate(raw_prompt)
    mandate_id = save_mandate(mandate)
    summary = check_existing_leads(
        mandate.industry,
        mandate.geography,
        mandate_id=mandate_id,
    )
    runs = create_source_runs_for_mandate(mandate_id)
    console.print(f"[bold]mandate_id[/bold]: {mandate_id}")
    summary_table = Table(title="Existing Lead Summary")
    summary_table.add_column("Field")
    summary_table.add_column("Value")
    for field, value in summary.model_dump().items():
        summary_table.add_row(field, str(value))
    console.print(summary_table)
    _print_planned_source_runs(runs)
    console.print("No external APIs were called. These are planned runs only.")


@app.command("source-runs")
def source_runs_command(
    mandate_id: str | None = typer.Option(None, is_flag=False),
) -> None:
    """List local source-run plans and mock-run outcomes."""
    query = "SELECT * FROM source_runs"
    parameters: tuple[str, ...] = ()
    if mandate_id:
        query += " WHERE mandate_id = ?"
        parameters = (mandate_id,)
    query += " ORDER BY created_at DESC, rowid DESC"
    with get_connection() as connection:
        runs = [dict(row) for row in connection.execute(query, parameters).fetchall()]
    table = Table(title="Source Runs")
    table.add_column("Run ID", width=8, no_wrap=True)
    table.add_column("Mandate", width=8, no_wrap=True)
    for column in (
        "Provider",
        "Source Type",
        "Query",
        "Status",
        "Est. Cost",
        "Found",
        "Imported",
    ):
        table.add_column(column)
    for run in runs:
        table.add_row(
            run["id"][:8],
            run["mandate_id"][:8],
            run["provider"],
            run["source_type"],
            run["query"],
            run["status"],
            f"${run['estimated_cost']:.2f}" if run["estimated_cost"] is not None else "-",
            str(run["records_found"]),
            str(run["records_imported"]),
        )
    console.print(table)
    console.print("You can use the short Run ID prefix with run-google-maps-mock.")


@app.command("run-google-maps-mock")
def run_google_maps_mock_command(
    source_run_id: str,
    limit: int = typer.Option(25, is_flag=False),
) -> None:
    """Execute one planned Google Maps run using synthetic leads only."""
    try:
        source_run = find_source_run_by_id_or_prefix(source_run_id)
    except ValueError as error:
        console.print(f"[red]{error}[/red]")
        raise typer.Exit(code=1) from error
    if source_run is None:
        console.print("[red]Source run not found. Run: python main.py source-runs[/red]")
        raise typer.Exit(code=1)
    source_identity = f"{source_run['provider']} {source_run['source_type']}".lower()
    if "apify" not in source_identity or "maps" not in source_identity:
        console.print("[red]Source run is not an Apify Google Maps plan.[/red]")
        raise typer.Exit(code=1)
    safe_statuses = {"approved", "planned", "approval_required", "completed_mock"}
    if source_run["status"] not in safe_statuses:
        console.print(
            f"[red]Source run status is not safe for mock execution: "
            f"{source_run['status']}[/red]"
        )
        raise typer.Exit(code=1)
    summary = run_apify_google_maps_mock(
        source_run["mandate_id"],
        source_run["id"],
        source_run["query"],
        limit=limit,
    )
    table = Table(title="Google Maps Mock Run")
    table.add_column("Field")
    table.add_column("Value")
    for field, value in summary.items():
        table.add_row(field, str(value))
    console.print(table)
    console.print("DRY RUN ONLY: No real Apify API call was made.")


@app.command("mock-enrich")
def mock_enrich_command(
    mandate_id: str | None = typer.Option(None, is_flag=False),
    limit: int = typer.Option(25, is_flag=False),
) -> None:
    """Generate synthetic contacts for companies lacking contacts."""
    contacts = enrich_companies_without_contacts(mandate_id=mandate_id, limit=limit)
    table = Table(title="Mock Email Enrichment")
    for column in ("Company", "Contact", "Title", "Email", "Email Status"):
        table.add_column(column)
    for contact in contacts:
        table.add_row(
            contact.company_name,
            contact.full_name or "-",
            contact.title or "-",
            contact.email or "-",
            contact.email_status,
        )
    console.print(table)
    console.print("DRY RUN ONLY: No real enrichment API was called.")


@app.command("mock-verify")
def mock_verify_command(
    mandate_id: str | None = typer.Option(None, is_flag=False),
    limit: int = typer.Option(100, is_flag=False),
) -> None:
    """Verify synthetic local emails without calling a provider."""
    results = verify_contacts_mock(mandate_id=mandate_id, limit=limit)
    table = Table(title="Mock Email Verification")
    for column in ("Email", "Old Status", "New Status", "Provider", "Reason"):
        table.add_column(column)
    for result in results:
        table.add_row(
            result.email,
            result.old_status or "-",
            result.new_status,
            result.verification_provider,
            result.reason,
        )
    console.print(table)

    counts = {
        status: sum(result.new_status == status for result in results)
        for status in ("valid", "catch_all", "risky", "invalid", "unknown")
    }
    console.print("[bold]Verification Summary[/bold]")
    for status, count in counts.items():
        console.print(f"{status}: {count}")
    console.print("DRY RUN ONLY: No real verification API was called.")


@app.command("research-tier-one")
def research_tier_one_command(
    mandate_id: str | None = typer.Option(None, is_flag=False),
    limit: int = typer.Option(25, is_flag=False),
    include_tier_two: bool = typer.Option(
        False,
        "--include-tier-two",
        help="Include Tier 2 companies in the local mock research pass.",
    ),
) -> None:
    """Generate mock research and personalization from local fields only."""
    results = research_tier_one_leads(
        mandate_id=mandate_id,
        limit=limit,
        include_tier_two=include_tier_two,
    )
    table = Table(title="Tier 1 Mock Research")
    for column in ("Company", "Contact", "Tier", "Score", "Opening Line", "Suggested CTA"):
        table.add_column(column)
    for result in results:
        table.add_row(
            result.company_name,
            result.contact_name or "-",
            result.priority_tier,
            str(result.fit_score),
            result.opening_line,
            result.suggested_cta,
        )
    console.print(table)
    console.print("DRY RUN ONLY: No Claude/API/web research was performed.")


@app.command("generate-email-copy")
def generate_email_copy_command(mandate_id: str) -> None:
    """Generate and save a local draft cold-email sequence."""
    save_email_sequence_for_mandate(mandate_id)
    sequence = get_latest_email_sequence(mandate_id)
    if sequence is None:
        console.print("[red]Email sequence was not saved.[/red]")
        raise typer.Exit(code=1)
    fields = (
        ("Campaign Name", "campaign_name"),
        ("Subject A", "subject_a"),
        ("Subject B", "subject_b"),
        ("Email 1", "email_1"),
        ("Email 2", "email_2"),
        ("Email 3", "email_3"),
        ("Unsubscribe Line", "unsubscribe_line"),
        ("Compliance Notes", "compliance_notes"),
    )
    table = Table(title="Draft Cold Email Sequence")
    table.add_column("Field")
    table.add_column("Value")
    for label, field in fields:
        table.add_row(label, str(sequence[field]))
    console.print(table)
    console.print("DRY RUN ONLY: No Claude API or Smartlead API was called.")


@app.command("email-sequences")
def email_sequences_command(
    mandate_id: str | None = typer.Option(None, is_flag=False),
) -> None:
    """List locally saved draft email sequences."""
    query = """
        SELECT
            email_sequences.*,
            campaigns.campaign_name,
            campaigns.mandate_id
        FROM email_sequences
        JOIN campaigns ON campaigns.id = email_sequences.campaign_id
    """
    parameters: tuple[str, ...] = ()
    if mandate_id:
        query += " WHERE campaigns.mandate_id = ?"
        parameters = (mandate_id,)
    query += " ORDER BY email_sequences.created_at DESC, email_sequences.rowid DESC"
    with get_connection() as connection:
        sequences = [
            dict(row) for row in connection.execute(query, parameters).fetchall()
        ]
    table = Table(title="Saved Email Sequences")
    for column in ("Sequence ID", "Campaign ID", "Campaign Name", "Subject A", "Created At"):
        table.add_column(column)
    for sequence in sequences:
        table.add_row(
            sequence["id"][:8],
            sequence["campaign_id"][:8],
            sequence["campaign_name"],
            sequence["subject_a"],
            sequence["created_at"],
        )
    console.print(table)


@app.command("mock-smartlead-deploy")
def mock_smartlead_deploy_command(
    mandate_id: str,
    limit: int = typer.Option(100, is_flag=False),
) -> None:
    """Mock-upload valid approved contacts to a paused local Smartlead campaign."""
    result = create_mock_smartlead_campaign(mandate_id, limit=limit)
    table = Table(title="Mock Smartlead Deploy")
    table.add_column("Field")
    table.add_column("Value")
    for field in (
        "campaign_name",
        "smartlead_campaign_id",
        "campaign_status",
        "leads_selected",
        "leads_uploaded",
        "sequence_attached",
    ):
        table.add_row(field, str(getattr(result, field)))
    console.print(table)
    console.print("DRY RUN ONLY: No real Smartlead campaign was created or launched.")


@app.command("campaign-leads")
def campaign_leads_command(
    mandate_id: str | None = typer.Option(None, is_flag=False),
) -> None:
    """List locally mock-uploaded campaign leads."""
    query = """
        SELECT
            campaign_leads.*,
            contacts.email,
            companies.company_name
        FROM campaign_leads
        JOIN campaigns ON campaigns.id = campaign_leads.campaign_id
        JOIN contacts ON contacts.id = campaign_leads.contact_id
        JOIN companies ON companies.id = contacts.company_id
    """
    parameters: tuple[str, ...] = ()
    if mandate_id:
        query += " WHERE campaigns.mandate_id = ?"
        parameters = (mandate_id,)
    query += " ORDER BY campaign_leads.created_at DESC, campaign_leads.rowid DESC"
    with get_connection() as connection:
        leads = [dict(row) for row in connection.execute(query, parameters).fetchall()]

    table = Table(title="Campaign Leads")
    for column in ("Campaign", "Contact Email", "Company", "Upload", "Approval"):
        table.add_column(column)
    for lead in leads:
        table.add_row(
            lead["campaign_id"][:8],
            lead["email"],
            lead["company_name"],
            lead["upload_status"],
            lead["approval_status"],
        )
    console.print(table)


@app.command("mock-campaign-report")
def mock_campaign_report_command(campaign_id: str) -> None:
    """Generate deterministic mock campaign reporting events."""
    summary = generate_mock_campaign_events(campaign_id)
    table = Table(title="Mock Campaign Report")
    table.add_column("Field")
    table.add_column("Value")
    for field, value in summary.model_dump().items():
        table.add_row(field, str(value))
    console.print(table)
    console.print("DRY RUN ONLY: No real Smartlead reporting sync was performed.")


@app.command("campaigns")
def campaigns_command() -> None:
    """List local campaign records."""
    with get_connection() as connection:
        campaigns = [
            dict(row)
            for row in connection.execute(
                """
                SELECT *
                FROM campaigns
                ORDER BY created_at DESC, rowid DESC
                """
            ).fetchall()
        ]
    table = Table(title="Campaigns")
    for column in (
        "Campaign",
        "Mandate",
        "Campaign Name",
        "Smartlead ID",
        "Status",
        "Created At",
    ):
        table.add_column(column)
    for campaign in campaigns:
        table.add_row(
            campaign["id"][:8],
            campaign["mandate_id"][:8],
            campaign["campaign_name"],
            campaign["smartlead_campaign_id"] or "-",
            campaign["campaign_status"],
            campaign["created_at"],
        )
    console.print(table)


@app.command("run-dry-pipeline")
def run_dry_pipeline_command(
    raw_prompt: str,
    limit: int = typer.Option(25, is_flag=False),
    reset_db: bool = typer.Option(False, "--reset-db", help="Reset and seed local SQLite first."),
) -> None:
    """Run the full local mock SOP pipeline without manual copy/paste IDs."""
    summary = run_dry_pipeline(raw_prompt, limit=limit, reset_db=reset_db)
    table = Table(title="Full Dry-Run Pipeline Summary")
    table.add_column("Field")
    table.add_column("Value")
    for field, value in summary.model_dump().items():
        table.add_row(field, str(value))
    console.print(table)
    console.print("DRY RUN ONLY: No external APIs were called and no campaign was launched.")


@app.callback()
def main(ctx: typer.Context) -> None:
    """Run the status command when no subcommand is provided."""
    if ctx.invoked_subcommand is None:
        status()


if __name__ == "__main__":
    app()
