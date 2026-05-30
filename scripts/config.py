"""Environment-backed configuration with safe defaults."""

import os

from dotenv import load_dotenv
from pydantic import BaseModel


class Settings(BaseModel):
    """Runtime settings. Dry-run mode defaults to enabled."""

    app_env: str = "development"
    dry_run: bool = True
    log_level: str = "INFO"
    default_budget_cap: float = 100.0
    anthropic_api_key: str = ""
    apify_api_token: str = ""
    apollo_api_key: str = ""
    consulti_api_key: str = ""
    hunter_api_key: str = ""
    millionverifier_api_key: str = ""
    turso_database_url: str = ""
    turso_auth_token: str = ""
    smartlead_api_key: str = ""
    winnr_api_key: str = ""
    winnr_account_email: str = ""


def get_settings() -> Settings:
    """Load runtime settings from `.env` and environment variables."""
    load_dotenv()
    return Settings(
        app_env=os.getenv("APP_ENV", "development"),
        dry_run=os.getenv("DRY_RUN", "true"),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        default_budget_cap=os.getenv("DEFAULT_BUDGET_CAP", "100"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        apify_api_token=os.getenv("APIFY_API_TOKEN", ""),
        apollo_api_key=os.getenv("APOLLO_API_KEY", ""),
        consulti_api_key=os.getenv("CONSULTI_API_KEY", ""),
        hunter_api_key=os.getenv("HUNTER_API_KEY", ""),
        millionverifier_api_key=os.getenv("MILLIONVERIFIER_API_KEY", ""),
        turso_database_url=os.getenv("TURSO_DATABASE_URL", ""),
        turso_auth_token=os.getenv("TURSO_AUTH_TOKEN", ""),
        smartlead_api_key=os.getenv("SMARTLEAD_API_KEY", ""),
        winnr_api_key=os.getenv("WINNR_API_KEY", ""),
        winnr_account_email=os.getenv("WINNR_ACCOUNT_EMAIL", ""),
    )
