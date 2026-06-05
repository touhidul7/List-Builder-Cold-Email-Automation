"""Settings page."""

import streamlit as st

from app.ui_helpers import show_dry_run_banner
from scripts.config import get_settings


def _configured(*values: str) -> str:
    return "configured" if all(values) else "missing"


def render() -> None:
    """Render safe configuration and setup notes without secrets."""
    st.title("Settings")
    show_dry_run_banner()
    settings = get_settings()
    st.subheader("Runtime")
    st.write(f"Environment: {settings.app_env}")
    st.write(f"DRY_RUN: {settings.dry_run}")
    st.write(f"Budget cap: {settings.default_budget_cap:g}")

    st.subheader("Integration Key Status")
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
        "Apify Google Maps Task": _configured(settings.apify_google_maps_task_id),
        "Real API Confirmation": _configured(settings.real_api_confirmation),
    }
    st.dataframe(
        [{"integration": name, "status": status} for name, status in integrations.items()],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Setup Commands")
    st.code(
        "pip install -r requirements.txt\n"
        "python -m scripts.init_db --reset --seed\n"
        "streamlit run app/streamlit_app.py",
        language="powershell",
    )
    st.info(
        "For real provider calls set DRY_RUN=false and "
        "REAL_API_CONFIRMATION=I_UNDERSTAND_REAL_API_CALLS. Paid actions must go "
        "through cost approval. No campaign launches without human approval."
    )
