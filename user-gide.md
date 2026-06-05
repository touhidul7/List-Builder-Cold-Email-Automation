# User Guide

This app can be used two ways:

1. In Claude Code, type prompts in plain English.
2. In a normal terminal, run `python main.py ...` commands directly.

Claude Code can run the terminal commands for you when you ask it to.

## First Prompt To Use In Claude Code

```text
Read CLAUDE.md, then run python main.py readiness and tell me what I should do next to use the app safely.
```

## Setup

Claude Code prompt:

```text
Read CLAUDE.md and README.md, then check whether this ListBuilder + ColdEmail AI app is set up correctly. Run the required setup/status commands and summarize what is ready.
```

Terminal commands:

```powershell
pip install -r requirements.txt
python -m scripts.init_db --reset --seed
python main.py status
python main.py readiness
```

## Start The Web UI

Claude Code prompt:

```text
Start the Streamlit web UI for this app and give me the localhost URL to open.
```

Terminal command:

```powershell
streamlit run app/streamlit_app.py
```

Open:

```text
http://localhost:8501
```

## Check Production Readiness

Claude Code prompt:

```text
Run python main.py readiness and explain what is done, partial, missing, and blocked against the SOP.
```

Terminal command:

```powershell
python main.py readiness
```

## Create A Mandate

Claude Code prompt:

```text
Create a mandate plan for: Find 25 acquisition targets for a client who wants to buy a commercial cleaning company in Ontario. Show me the mandate, ICP, source plan, and approval records created.
```

Terminal command:

```powershell
python main.py create-mandate-plan "Find 25 acquisition targets for a client who wants to buy a commercial cleaning company in Ontario."
```

## Run Full Dry Workflow

Claude Code prompt:

```text
Run the full dry-run pipeline for: Find 25 acquisition targets for a client who wants to buy a commercial cleaning company in Ontario. Do not call external APIs. Summarize the created leads, scores, email copy, and campaign records.
```

Terminal command:

```powershell
python main.py run-dry-pipeline "Find 25 acquisition targets for a client who wants to buy a commercial cleaning company in Ontario."
```

To reset the local database first:

```powershell
python main.py run-dry-pipeline "Find 25 acquisition targets for a client who wants to buy a commercial cleaning company in Ontario." --reset-db
```

## Check Existing Leads

Claude Code prompt:

```text
Check existing local leads for a mandate about commercial cleaning companies in Ontario before any paid sourcing.
```

Terminal command:

```powershell
python main.py existing-check "Find 25 acquisition targets for a client who wants to buy a commercial cleaning company in Ontario."
```

## Review Cost Approvals

Claude Code prompt:

```text
Show pending cost approvals. Explain what each paid action is for, then ask me before marking any approval as approved.
```

Terminal command example:

```powershell
python main.py cost-approval --provider apify --action-type scrape --estimated-cost 3 --description "Run Apify Google Maps scraper for commercial cleaning companies in Ontario" --reason "Need local business leads for this mandate" --expected-output "25-100 company records with names, websites, phones, and Google Maps URLs"
```

Approval command example:

```powershell
python main.py cost-approval --provider apify --action-type scrape --estimated-cost 3 --description "Run Apify Google Maps scraper for commercial cleaning companies in Ontario" --reason "Need local business leads for this mandate" --expected-output "25-100 company records with names, websites, phones, and Google Maps URLs" --response YES --approved-by Mark
```

## Score Leads

Claude Code prompt:

```text
Score the leads for the latest active mandate and show Tier 1, Tier 2, Tier 3, and rejected counts.
```

Terminal command:

```powershell
python main.py score-leads
```

## Research Tier 1 Leads

Claude Code prompt:

```text
Generate mock Tier 1 research for the latest mandate using only local database fields. Do not browse websites or call external APIs.
```

Terminal command:

```powershell
python main.py research-tier-one
```

## Generate Email Copy

Claude Code prompt:

```text
Generate compliant cold email copy for the latest mandate. Keep it short, plain text, no fake claims, no confidential details, and no external API calls.
```

Terminal command:

```powershell
python main.py generate-email-copy MANDATE_ID
```

List saved sequences:

```powershell
python main.py email-sequences
```

## Create Mock Smartlead Campaign

Claude Code prompt:

```text
Create a paused mock Smartlead campaign for the latest mandate using only valid approved local leads. Do not call Smartlead and do not send email.
```

Terminal command:

```powershell
python main.py mock-smartlead-deploy MANDATE_ID
```

View campaigns:

```powershell
python main.py campaigns
python main.py campaign-leads
```

## Mock Campaign Reporting

Claude Code prompt:

```text
Generate mock campaign reporting events for the selected campaign. Do not call Smartlead.
```

Terminal command:

```powershell
python main.py mock-campaign-report CAMPAIGN_ID
```

## Real Apollo

Claude Code prompt:

```text
Check whether real Apollo is safely configured. If DRY_RUN=false, REAL_API_CONFIRMATION is set, Apollo API key exists, and there is an approved cost approval, run a small Apollo People Search for the current mandate. Otherwise tell me exactly what is missing.
```

Use the web UI:

```text
Real Tools -> Apollo
```

## Real Apify

Claude Code prompt:

```text
Check whether real Apify Google Maps is safely configured. If all real-mode gates and approvals are satisfied, run the configured Apify task for a small test scrape. Otherwise tell me exactly what is missing.
```

Use the web UI:

```text
Real Tools -> Apify
```

## Real Smartlead Draft

Claude Code prompt:

```text
Check whether real Smartlead draft campaign creation is safely configured. If all gates and approvals are satisfied, create only a draft campaign. Do not upload senders, launch, or send email.
```

Use the web UI:

```text
Real Tools -> Smartlead
```

## Import Real CSV Leads

Claude Code prompt:

```text
Guide me through importing a real lead CSV into the web UI. Confirm the required columns and remind me that email_status should only be valid if already verified.
```

Use the web UI:

```text
Real Data Import
```

Minimum CSV column:

```text
company_name
```

Recommended CSV columns:

```text
company_name,website,industry,city,province,country,phone,source,source_url,full_name,title,email,email_status,previously_contacted
```

## Continue Development

Claude Code prompt:

```text
Open the Production Readiness checklist and implement the next missing production feature safely, preserving approval gates and no automatic sending.
```

Terminal command:

```powershell
python main.py readiness
```

## Safety Rules

- Keep `DRY_RUN=true` unless you intentionally want a real provider action.
- Do not send email automatically.
- Do not launch Smartlead campaigns automatically.
- Require approval before paid provider usage.
- Use Smartlead real mode only for draft campaign creation until full lead upload, sequence upload, sender assignment, and sync are implemented.
- Consulti, Hunter, MillionVerifier, Winnr, and full Smartlead upload/sync are still production gaps unless the readiness page says otherwise.

