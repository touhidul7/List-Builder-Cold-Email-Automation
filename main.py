"""CLI entry point for ListBuilder + ColdEmail AI."""

import typer
from rich.console import Console
from rich.table import Table

from scripts.config import get_settings

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


@app.callback()
def main(ctx: typer.Context) -> None:
    """Run the status command when no subcommand is provided."""
    if ctx.invoked_subcommand is None:
        status()


if __name__ == "__main__":
    app()
