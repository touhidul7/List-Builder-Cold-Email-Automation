# Build Plan

## Completed dry-run modules

- Project setup, config, CLI, and local SQLite database.
- Mandate intake, mandate saving, ICP builder, and existing lead check.
- Lead source planning, source-run planning, and pending cost approvals.
- Mock Apify Google Maps import with duplicate checks and fingerprints.
- Mock email enrichment and mock email verification.
- Lead scoring, priority tiers, and company score persistence.
- Mock Tier 1 research and personalization.
- Mock cold-email strategy and copywriting.
- Mock paused Smartlead campaign deployment.
- Mock campaign reporting events.
- Full end-to-end `run-dry-pipeline` command.

## Real credential connection order

1. Turso
2. Apify
3. Hunter/Consulti
4. MillionVerifier
5. Apollo
6. Smartlead
7. Winnr
8. Anthropic/Claude API if needed

## Safety notes

- Keep `DRY_RUN=true` until each real integration has credentials, approval gates, and tests.
- No paid provider action should run without explicit approval.
- No Smartlead campaign should launch automatically.
