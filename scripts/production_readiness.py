"""SOP readiness inventory for CLI and Streamlit.

This module is intentionally declarative. It does not call providers or mutate
state; it explains whether each SOP capability is implemented, safely gated, or
still needs provider-specific build work.
"""

from dataclasses import dataclass
from typing import Literal

from scripts.config import Settings, get_settings


ReadinessStatus = Literal["done", "partial", "missing", "blocked"]
Surface = Literal["CLI", "Web UI", "Backend", "Claude Code"]


@dataclass(frozen=True)
class ReadinessItem:
    """One SOP capability and its current implementation state."""

    area: str
    requirement: str
    status: ReadinessStatus
    surfaces: tuple[Surface, ...]
    evidence: str
    next_step: str


def _configured(settings: Settings, *values: str) -> bool:
    """Return whether required setting values are present."""
    return all(bool(value) for value in values)


def get_readiness_items(settings: Settings | None = None) -> list[ReadinessItem]:
    """Return the current SOP readiness checklist."""
    settings = settings or get_settings()
    apollo_ready = _configured(settings, settings.apollo_api_key)
    apify_ready = _configured(settings, settings.apify_api_token, settings.apify_google_maps_task_id)
    smartlead_ready = _configured(settings, settings.smartlead_api_key)
    turso_configured = _configured(settings, settings.turso_database_url, settings.turso_auth_token)
    consulti_configured = _configured(settings, settings.consulti_api_key)
    hunter_configured = _configured(settings, settings.hunter_api_key)
    millionverifier_configured = _configured(settings, settings.millionverifier_api_key)
    winnr_configured = _configured(settings, settings.winnr_api_key, settings.winnr_account_email)
    real_mode_ready = not settings.dry_run and settings.real_api_confirmation == "I_UNDERSTAND_REAL_API_CALLS"

    return [
        ReadinessItem(
            "Mandate",
            "Capture mandate, build ICP, and create source plan.",
            "done",
            ("CLI", "Web UI", "Backend"),
            "Implemented by intake, icp, source-plan, save-mandate, create-mandate-plan, and New Mandate page.",
            "Use the New Mandate page or python main.py create-mandate-plan.",
        ),
        ReadinessItem(
            "Duplicate Control",
            "Check stored records before paid sourcing, enrichment, verification, or campaign upload.",
            "done",
            ("CLI", "Web UI", "Backend"),
            "Existing-lead check, fingerprints, duplicate preview, and unique indexes are implemented locally.",
            "Run existing-check/update-fingerprints/dedupe-preview before paid actions.",
        ),
        ReadinessItem(
            "Cost Control",
            "Record human approval before paid or external actions.",
            "done",
            ("CLI", "Web UI", "Backend"),
            "Cost approvals are stored locally and real provider helpers require approved records.",
            "Approve records in Cost Approvals before using Real Tools.",
        ),
        ReadinessItem(
            "Real Mode Gate",
            "Block live API calls unless real mode is explicitly enabled.",
            "done" if real_mode_ready else "partial",
            ("Web UI", "Backend"),
            "Live calls require DRY_RUN=false, REAL_API_CONFIRMATION, API key, and approval_id.",
            "Set DRY_RUN=false and REAL_API_CONFIRMATION only when you intend to spend credits.",
        ),
        ReadinessItem(
            "Database",
            "Store mandates, companies, contacts, scoring, domains, inboxes, campaigns, and events.",
            "partial" if turso_configured else "partial",
            ("CLI", "Web UI", "Backend"),
            "Schema is Turso/libSQL-compatible, but runtime currently writes local SQLite.",
            "Add libSQL/Turso connection switching before calling this fully production Turso.",
        ),
        ReadinessItem(
            "Apify Google Maps",
            "Run approved Google Maps scraping for local business leads.",
            "partial" if apify_ready else "partial",
            ("Web UI", "Backend"),
            "Real Apify task runner exists; it depends on APIFY_GOOGLE_MAPS_TASK_ID and approval.",
            "Configure and test an Apify task payload for each actor/source type.",
        ),
        ReadinessItem(
            "Apollo",
            "Run approved Apollo people/company discovery.",
            "partial" if apollo_ready else "partial",
            ("Web UI", "Backend"),
            "Apollo People Search is implemented and imports records locally, but it does not reveal emails.",
            "Use Apollo for discovery, then route missing emails through approved enrichment.",
        ),
        ReadinessItem(
            "Consulti",
            "Use Consulti for B2B/local lead pull, enrichment, and primary verification.",
            "missing" if consulti_configured else "blocked",
            ("Backend",),
            "Consulti scripts are placeholders and do not call the provider.",
            "Implement provider-specific Consulti endpoints after confirming API docs and allowed usage.",
        ),
        ReadinessItem(
            "Hunter",
            "Use Hunter only for missing emails on high-fit Google Maps leads with websites.",
            "missing" if hunter_configured else "blocked",
            ("Backend",),
            "Hunter script is a placeholder.",
            "Implement gated Hunter domain search and enforce missing-email/high-fit rules.",
        ),
        ReadinessItem(
            "MillionVerifier",
            "Use MillionVerifier as backup verification when Consulti is unavailable.",
            "missing" if millionverifier_configured else "blocked",
            ("Backend",),
            "MillionVerifier script is a placeholder.",
            "Implement backup verification only after Consulti fallback rules are explicit.",
        ),
        ReadinessItem(
            "Lead Processing",
            "Enrich, verify, dedupe, score, and research only top leads.",
            "partial",
            ("CLI", "Web UI", "Backend"),
            "Local mock enrichment/verification, dedupe, scoring, and Tier 1 research are implemented.",
            "Replace mock enrichment/verification with gated real provider calls where required.",
        ),
        ReadinessItem(
            "Cold Email Copy",
            "Generate compliant short plain-text cold email sequence.",
            "done",
            ("CLI", "Web UI", "Backend"),
            "Local email strategy/copy generation persists draft sequences and does not call external APIs.",
            "Review copy before any Smartlead upload.",
        ),
        ReadinessItem(
            "Winnr",
            "Purchase domains and create inboxes after human approval.",
            "missing" if winnr_configured else "blocked",
            ("Backend",),
            "Domain/inbox tables exist; Winnr purchase/create scripts are placeholders.",
            "Implement Winnr API with budget, approval, DNS, warmup, and sender upload checks.",
        ),
        ReadinessItem(
            "Smartlead",
            "Create paused campaigns, upload approved leads/sequences, and sync results.",
            "partial" if smartlead_ready else "partial",
            ("CLI", "Web UI", "Backend"),
            "Mock paused deploy works; real draft campaign creation works. Real lead/sequence upload and result sync are placeholders.",
            "Implement lead upload, merge fields, sequence upload, sender assignment, and read-only result sync.",
        ),
        ReadinessItem(
            "Claude Code",
            "Operate the app from Claude Code as required by the SOP.",
            "done",
            ("Claude Code", "CLI"),
            "The app is a normal terminal CLI that runs inside Claude Code's terminal with python main.py commands.",
            "Open the repo in Claude Code, install requirements, initialize DB, then run python main.py --help.",
        ),
        ReadinessItem(
            "Web UI",
            "Expose a professional dashboard for the workflow.",
            "partial",
            ("Web UI",),
            "Streamlit UI covers the dry workflow, real CSV import, real Apollo/Apify/Smartlead draft tools, and status pages.",
            "Add production workbench surfaces for missing integrations and improve visual polish.",
        ),
    ]


def summarize_readiness(items: list[ReadinessItem] | None = None) -> dict[str, int]:
    """Return counts by readiness status."""
    items = items or get_readiness_items()
    counts = {"done": 0, "partial": 0, "missing": 0, "blocked": 0}
    for item in items:
        counts[item.status] += 1
    return counts

