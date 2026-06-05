# Claude Code Operating Guide

This project works in Claude Code as a normal terminal-driven Python app.
There is no separate proprietary Claude Code CLI command. Open this repository
in Claude Code and run the same commands you would run in PowerShell.

## First Run

```powershell
pip install -r requirements.txt
python -m scripts.init_db --reset --seed
python main.py --help
python main.py readiness
```

## Local Dry-Run Workflow

```powershell
python main.py run-dry-pipeline "Find 25 acquisition targets for a client who wants to buy a commercial cleaning company in Ontario."
python main.py db-status
```

Dry-run mode is the default. It does not call external APIs, spend credits,
create real Smartlead campaigns, or send email.

## Web UI

```powershell
streamlit run app/streamlit_app.py
```

Open the Streamlit URL shown in the terminal. Use Production Readiness to see
which SOP items are implemented, partial, missing, or blocked.

## Real Provider Boundary

Real provider actions are blocked unless all required gates are satisfied:

```env
DRY_RUN=false
REAL_API_CONFIRMATION=I_UNDERSTAND_REAL_API_CALLS
```

The provider API key must be configured, and the action must reference an
approved cost approval record. No campaign launch or email sending is currently
implemented.

## Current Production Gap

The app has real Apollo People Search, real Apify task execution, and real
Smartlead draft campaign creation. Consulti, Hunter, MillionVerifier, Winnr,
Smartlead lead/sequence upload, and Smartlead result sync still need
provider-specific implementation before the SOP is fully production complete.

