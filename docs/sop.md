# Standard Operating Procedure

## Status

The current application implements the SOP as a safe local workflow plus a
limited set of approval-gated real provider actions.

Use `python main.py readiness` or the Streamlit `Production Readiness` page for
the live checklist.

## Required sequence

1. Capture the client mandate.
2. Confirm the ICP and source plan.
3. Check stored leads before purchasing data.
4. Estimate cost and obtain human approval.
5. Collect, enrich, verify, deduplicate, and score leads.
6. Review compliance and QA checklists.
7. Generate copy and deploy Smartlead campaigns as paused drafts only.

## Implemented production surfaces

- Normal terminal CLI: `python main.py --help`.
- Claude Code usage: open the repo and run the same terminal commands.
- Streamlit UI: `streamlit run app/streamlit_app.py`.
- Real provider actions currently available behind gates:
  - Apollo People Search.
  - Apify configured Google Maps task.
  - Smartlead draft campaign creation.

## Still not fully implemented

- Remote Turso/libSQL runtime connection. The schema is compatible, but runtime
  writes local SQLite.
- Real Consulti lead pull/enrichment/verification.
- Real Hunter enrichment.
- Real MillionVerifier backup verification.
- Real Winnr domain/inbox purchase.
- Real Smartlead approved lead upload, sequence upload, sender upload, campaign
  launch approval, and result sync.
