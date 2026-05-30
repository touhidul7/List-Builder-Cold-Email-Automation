-- Initial Turso-compatible SQLite schema.
-- Apply only when database initialization is explicitly requested.

CREATE TABLE IF NOT EXISTS mandates (
    id INTEGER PRIMARY KEY,
    client_name TEXT NOT NULL,
    objective TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY,
    company_name TEXT NOT NULL,
    domain TEXT,
    contact_name TEXT,
    email TEXT,
    source TEXT NOT NULL,
    fingerprint TEXT NOT NULL UNIQUE,
    score INTEGER,
    verification_status TEXT NOT NULL DEFAULT 'unverified',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cost_approvals (
    id INTEGER PRIMARY KEY,
    mandate_id INTEGER NOT NULL,
    provider TEXT NOT NULL,
    estimated_cost REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    approved INTEGER NOT NULL DEFAULT 0 CHECK (approved IN (0, 1)),
    approved_by TEXT,
    approved_at TEXT,
    FOREIGN KEY (mandate_id) REFERENCES mandates(id)
);

CREATE TABLE IF NOT EXISTS campaign_drafts (
    id INTEGER PRIMARY KEY,
    mandate_id INTEGER NOT NULL,
    smartlead_campaign_id TEXT,
    status TEXT NOT NULL DEFAULT 'paused',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (mandate_id) REFERENCES mandates(id)
);

