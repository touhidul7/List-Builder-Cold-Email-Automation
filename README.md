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

## Safety rules

- Never commit `.env` or real credentials.
- Keep `DRY_RUN=true` unless a human explicitly approves a controlled run.
- Do not send email automatically.
- Deploy Smartlead campaigns in a paused state only.
- Record approval before future paid API calls.
