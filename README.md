# ListBuilder + ColdEmail AI

Backend/CLI automation scaffold for building qualified lead lists and preparing
paused cold-email campaigns. This repository is intentionally safe by default:
`DRY_RUN=true`, no API calls are implemented, and paid actions require an
explicit approval gate before future execution.

## Planned workflow

1. Capture and validate a client mandate.
2. Build an ICP and plan suitable lead sources.
3. Check existing leads and estimate paid-source costs.
4. Require human cost approval before any paid API usage.
5. Store, enrich, verify, deduplicate, and score leads.
6. Generate cold-email strategy and copy.
7. Deploy only paused Smartlead campaigns for human review.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python main.py
python main.py plan
```

`python main.py` runs the `status` command by default. You can also run it
explicitly with `python main.py status`.

## Local Database Setup

Create a fresh local SQLite database with synthetic seed data:

```powershell
python -m scripts.init_db --reset --seed
python main.py db-status
```

The local database is created at `data/local_dev.db`. This workflow does not
connect to Turso or call external APIs.

## Mandate Intake

Parse natural-language mandates locally with deterministic rules:

```powershell
python main.py intake "Find 25 acquisition targets for a client who wants to buy a commercial cleaning company in Ontario."
python main.py intake "Find family offices in Toronto."
python main.py intake "Find investors for an Oakville gym."
```

## ICP Builder

Build a deterministic ICP profile from an intake prompt:

```powershell
python main.py icp "Find 25 acquisition targets for a client who wants to buy a commercial cleaning company in Ontario."
python main.py icp "Find family offices in Toronto."
python main.py icp "Find investors for an Oakville gym."
```

## Lead Source Planner

Create a review-only source plan without running external integrations:

```powershell
python main.py source-plan "Find 25 acquisition targets for a client who wants to buy a commercial cleaning company in Ontario."
python main.py source-plan "Find family offices in Toronto."
python main.py source-plan "Find investors for an Oakville gym."
python main.py source-plan "Find strategic buyers for a commercial cleaning company in Canada."
```

## Cost Approval Gate

Create and record a pending local approval request:

```powershell
python main.py cost-approval --provider apify --action-type scrape --estimated-cost 3 --description "Run Apify Google Maps scraper for commercial cleaning companies in Ontario" --reason "Need local business leads for this mandate" --expected-output "25-100 company records with names, websites, phones, and Google Maps URLs"
```

Record an explicit local approval:

```powershell
python main.py cost-approval --provider apify --action-type scrape --estimated-cost 3 --description "Run Apify Google Maps scraper for commercial cleaning companies in Ontario" --reason "Need local business leads for this mandate" --expected-output "25-100 company records with names, websites, phones, and Google Maps URLs" --response YES --approved-by Mark
```

These commands only record an approval decision. They never call or charge a
provider.

## Local Mandates And Existing Leads

Persist parsed mandates and check local records before paid sourcing:

```powershell
python main.py save-mandate "Find 25 acquisition targets for a client who wants to buy a commercial cleaning company in Ontario."
python main.py mandates
python main.py existing-check "Find 25 acquisition targets for a client who wants to buy a commercial cleaning company in Ontario."
```

## Safety rules

- Never commit `.env` or real credentials.
- Keep `DRY_RUN=true` unless a human explicitly approves a controlled run.
- Do not send email automatically.
- Deploy Smartlead campaigns in a paused state only.
- Record approval before future paid API calls.
