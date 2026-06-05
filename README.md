# ListBuilder + ColdEmail AI

Backend/CLI automation scaffold for building qualified lead lists and preparing
paused cold-email campaigns. This repository is intentionally safe by default:
`DRY_RUN=true`, live API calls are blocked unless explicitly enabled, and paid
actions require an approval gate before execution.

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
python main.py readiness
```

`python main.py` runs the `status` command by default. You can also run it
explicitly with `python main.py status`.

## Claude Code Usage

This app works in Claude Code as a normal terminal-driven Python app. Open this
repository in Claude Code and run the same commands shown above in the Claude
Code terminal. There is no separate Claude Code-only command layer required.
See `CLAUDE.md` for the operating guide.

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

## Lead Scoring

Score local companies using the SOP scoring model:

```powershell
python main.py score-leads
python main.py score-leads --mandate-id YOUR_MANDATE_ID
```

## Lead Deduplication

Update fingerprints and preview possible local duplicates without deleting records:

```powershell
python main.py update-fingerprints
python main.py dedupe-preview
python main.py duplicate-check --company-name "ABC Cleaning" --website "https://abccleaning.ca" --city "Toronto" --phone "416-555-1234"
```

## Source Run Planner

Persist source-run plans and pending cost approvals without calling providers:

```powershell
python main.py save-mandate "Find 25 acquisition targets for a client who wants to buy a commercial cleaning company in Ontario."
python main.py mandates
python main.py plan-runs YOUR_MANDATE_ID
python main.py create-mandate-plan "Find 25 acquisition targets for a client who wants to buy a commercial cleaning company in Ontario."
python main.py db-status
```

## Google Maps Mock Runner

Generate and store synthetic Google Maps leads without calling Apify:

```powershell
python -m scripts.init_db --reset --seed
python main.py create-mandate-plan "Find 25 acquisition targets for a client who wants to buy a commercial cleaning company in Ontario."
python main.py source-runs
python main.py run-google-maps-mock SOURCE_RUN_ID
python main.py mock-enrich
python main.py mock-verify
python main.py score-leads
python main.py research-tier-one
python main.py generate-email-copy MANDATE_ID
python main.py mock-smartlead-deploy MANDATE_ID
python main.py campaigns
python main.py campaign-leads
python main.py email-sequences
python main.py db-status
```

## Full Dry-Run Workflow

Run the complete local mock SOP without manually copying a source run ID:

```powershell
python main.py run-dry-pipeline "Find 25 acquisition targets for a client who wants to buy a commercial cleaning company in Ontario." --reset-db
```

Manual dry-run workflow:

```powershell
python -m scripts.init_db --reset --seed
python main.py create-mandate-plan "Find 25 acquisition targets for a client who wants to buy a commercial cleaning company in Ontario."
python main.py source-runs
python main.py run-google-maps-mock SOURCE_RUN_ID
python main.py mock-enrich
python main.py mock-verify
python main.py score-leads
python main.py research-tier-one
python main.py generate-email-copy MANDATE_ID
python main.py mock-smartlead-deploy MANDATE_ID
python main.py campaigns
python main.py campaign-leads
python main.py db-status
```

## Mock Email Enrichment

Create synthetic contacts for companies that do not have contacts yet:

```powershell
python main.py mock-enrich
python main.py mock-enrich --mandate-id YOUR_MANDATE_ID --limit 25
```

This command only inserts fake local contacts. It never calls Hunter, Consulti,
or another external enrichment provider.

## Mock Email Verification

Classify synthetic local emails without calling Consulti or MillionVerifier:

```powershell
python main.py mock-verify
python main.py mock-verify --mandate-id YOUR_MANDATE_ID --limit 100
```

## Tier 1 Mock Research

Create safe personalization for scored Tier 1 leads using local database fields only:

```powershell
python main.py research-tier-one
python main.py research-tier-one --mandate-id YOUR_MANDATE_ID --limit 25
python main.py research-tier-one --include-tier-two
```

This command does not call Claude, browse websites, or call external APIs.

## Mock Cold Email Copy

Generate and list local draft email sequences without calling Claude or Smartlead:

```powershell
python main.py generate-email-copy MANDATE_ID
python main.py email-sequences
python main.py email-sequences --mandate-id MANDATE_ID
```

## Mock Smartlead Deploy And Reporting

Create a paused local campaign, mock-upload valid approved leads, and generate
synthetic reporting events:

```powershell
python main.py mock-smartlead-deploy MANDATE_ID
python main.py campaigns
python main.py campaign-leads
python main.py mock-campaign-report CAMPAIGN_ID
```

These commands never call Smartlead, never send email, and never launch a
campaign.

## Streamlit Dashboard

Run the browser dashboard for the same local dry-run workflow:

```powershell
pip install -r requirements.txt
python -m scripts.init_db --reset --seed
streamlit run app/streamlit_app.py
```

The dashboard runs at http://localhost:8501. API keys stay server-side in `.env`;
use the Settings page to check whether each integration is configured or missing.

### Real Data Workflow

Use the dashboard with real lead data you already have:

1. Create a mandate on the New Mandate page.
2. Open Real Data Import.
3. Upload a CSV with at least `company_name`.
4. Recommended columns:

```text
company_name,website,industry,city,province,country,phone,source,source_url,full_name,title,email,email_status,previously_contacted
```

5. Confirm permission and import the CSV.
6. Use Leads, Scoring, Research, Email Copy, and Campaigns for review.

Imported records are real local records in `data/local_dev.db`. Email statuses
are trusted as user-supplied; set `email_status=valid` only when you have already
verified the address. The app still does not send email or launch campaigns.

### Real External Tools

The Real Tools page can call approved external providers. Real calls are blocked
unless all of these are true:

```env
DRY_RUN=false
REAL_API_CONFIRMATION=I_UNDERSTAND_REAL_API_CALLS
APOLLO_API_KEY=...
APIFY_API_TOKEN=...
APIFY_GOOGLE_MAPS_TASK_ID=...
SMARTLEAD_API_KEY=...
```

You must also approve a cost approval record before running a real provider
action. Use Cost Approvals to mark an action approved.

Currently implemented real external actions:

- Apollo People Search: imports people and companies into local SQLite. Apollo
  People Search does not return email addresses.
- Apify Google Maps task: runs your configured Apify task and imports returned
  company records.
- Smartlead draft campaign creation: creates a Smartlead draft campaign only.
  It does not add senders, start a campaign, or send emails.

Hunter, Consulti, MillionVerifier, Winnr, and Smartlead sending are still not
implemented because those require separate provider-specific setup and stronger
approval controls.

## Safety rules

- Never commit `.env` or real credentials.
- Keep `DRY_RUN=true` unless a human explicitly approves a controlled run.
- Do not send email automatically.
- Deploy Smartlead campaigns in a paused state only.
- Record approval before future paid API calls.
