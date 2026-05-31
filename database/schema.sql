-- SQLite-compatible schema for Turso/libSQL.
-- Apply only when database initialization is explicitly requested.

CREATE TABLE IF NOT EXISTS mandates (
    id TEXT PRIMARY KEY,
    mandate_name TEXT,
    mandate_type TEXT,
    industry TEXT,
    geography TEXT,
    target_lead_count INTEGER,
    campaign_goal TEXT,
    company_size TEXT,
    target_titles TEXT,
    exclusions TEXT,
    budget_cap REAL DEFAULT 100,
    amount_spent REAL DEFAULT 0,
    status TEXT DEFAULT 'active',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS companies (
    id TEXT PRIMARY KEY,
    mandate_id TEXT,
    company_name TEXT NOT NULL,
    website TEXT,
    root_domain TEXT,
    industry TEXT,
    city TEXT,
    province TEXT,
    country TEXT,
    phone TEXT,
    source TEXT,
    source_url TEXT,
    google_place_id TEXT,
    apollo_company_id TEXT,
    consulti_company_id TEXT,
    apify_run_id TEXT,
    source_fingerprint TEXT,
    fit_score INTEGER,
    confidence_score INTEGER,
    priority_tier TEXT,
    score_reason TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (mandate_id) REFERENCES mandates(id)
);

CREATE TABLE IF NOT EXISTS contacts (
    id TEXT PRIMARY KEY,
    company_id TEXT,
    full_name TEXT,
    title TEXT,
    email TEXT,
    email_status TEXT,
    phone TEXT,
    source TEXT,
    verification_provider TEXT,
    apollo_contact_id TEXT,
    consulti_contact_id TEXT,
    source_fingerprint TEXT,
    last_verified_at TEXT,
    last_enriched_at TEXT,
    previously_contacted INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

CREATE TABLE IF NOT EXISTS personalization (
    id TEXT PRIMARY KEY,
    contact_id TEXT,
    opening_line TEXT,
    fit_rationale TEXT,
    outreach_angle TEXT,
    suggested_cta TEXT,
    research_notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contact_id) REFERENCES contacts(id)
);

CREATE TABLE IF NOT EXISTS campaigns (
    id TEXT PRIMARY KEY,
    mandate_id TEXT,
    smartlead_campaign_id TEXT,
    campaign_name TEXT,
    campaign_status TEXT DEFAULT 'paused',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (mandate_id) REFERENCES mandates(id)
);

CREATE TABLE IF NOT EXISTS outreach_events (
    id TEXT PRIMARY KEY,
    contact_id TEXT,
    campaign_id TEXT,
    event_type TEXT,
    event_date TEXT DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
);

CREATE TABLE IF NOT EXISTS domains (
    id TEXT PRIMARY KEY,
    domain_name TEXT UNIQUE,
    provider TEXT DEFAULT 'winnr',
    status TEXT,
    purchase_date TEXT DEFAULT CURRENT_TIMESTAMP,
    renewal_date TEXT,
    campaign_id TEXT,
    notes TEXT,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
);

CREATE TABLE IF NOT EXISTS inboxes (
    id TEXT PRIMARY KEY,
    domain_id TEXT,
    email_address TEXT UNIQUE,
    provider TEXT DEFAULT 'winnr',
    smartlead_sender_id TEXT,
    status TEXT,
    warmup_status TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (domain_id) REFERENCES domains(id)
);

CREATE TABLE IF NOT EXISTS cost_approvals (
    id TEXT PRIMARY KEY,
    mandate_id TEXT,
    action_type TEXT,
    action_description TEXT,
    provider TEXT,
    estimated_cost REAL,
    actual_cost REAL,
    estimated_credits INTEGER,
    approval_status TEXT DEFAULT 'pending',
    approved_by TEXT,
    approved_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (mandate_id) REFERENCES mandates(id)
);

CREATE TABLE IF NOT EXISTS source_runs (
    id TEXT PRIMARY KEY,
    mandate_id TEXT,
    provider TEXT,
    source_type TEXT,
    query TEXT,
    status TEXT DEFAULT 'planned',
    estimated_cost REAL,
    actual_cost REAL,
    raw_output_path TEXT,
    records_found INTEGER DEFAULT 0,
    records_imported INTEGER DEFAULT 0,
    started_at TEXT,
    finished_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (mandate_id) REFERENCES mandates(id)
);

CREATE TABLE IF NOT EXISTS lead_scores (
    id TEXT PRIMARY KEY,
    company_id TEXT,
    icp_fit INTEGER DEFAULT 0,
    geography_fit INTEGER DEFAULT 0,
    company_size_fit INTEGER DEFAULT 0,
    contact_quality INTEGER DEFAULT 0,
    email_quality INTEGER DEFAULT 0,
    source_confidence INTEGER DEFAULT 0,
    strategic_relevance INTEGER DEFAULT 0,
    total_score INTEGER DEFAULT 0,
    priority_tier TEXT,
    score_reason TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

CREATE TABLE IF NOT EXISTS research_logs (
    id TEXT PRIMARY KEY,
    company_id TEXT,
    contact_id TEXT,
    research_type TEXT,
    research_summary TEXT,
    personalization_notes TEXT,
    source_urls TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id)
);

CREATE TABLE IF NOT EXISTS email_sequences (
    id TEXT PRIMARY KEY,
    campaign_id TEXT,
    sequence_name TEXT,
    subject_a TEXT,
    subject_b TEXT,
    email_1 TEXT,
    email_2 TEXT,
    email_3 TEXT,
    email_4 TEXT,
    unsubscribe_line TEXT,
    compliance_notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
);

CREATE TABLE IF NOT EXISTS campaign_leads (
    id TEXT PRIMARY KEY,
    campaign_id TEXT,
    contact_id TEXT,
    smartlead_lead_id TEXT,
    upload_status TEXT,
    approval_status TEXT DEFAULT 'pending',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS unique_company_domain
    ON companies(root_domain)
    WHERE root_domain IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS unique_contact_email
    ON contacts(email)
    WHERE email IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS unique_google_place
    ON companies(google_place_id)
    WHERE google_place_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS unique_apollo_company
    ON companies(apollo_company_id)
    WHERE apollo_company_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS unique_consulti_company
    ON companies(consulti_company_id)
    WHERE consulti_company_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_company_name_city
    ON companies(company_name, city);

CREATE INDEX IF NOT EXISTS idx_company_industry_geo
    ON companies(industry, province, country);

CREATE INDEX IF NOT EXISTS idx_contacts_company_id
    ON contacts(company_id);

CREATE INDEX IF NOT EXISTS idx_cost_approvals_mandate_id
    ON cost_approvals(mandate_id);

CREATE INDEX IF NOT EXISTS idx_campaign_leads_campaign_id
    ON campaign_leads(campaign_id);
