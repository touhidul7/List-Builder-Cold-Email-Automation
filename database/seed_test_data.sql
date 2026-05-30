-- Synthetic local test data only.

INSERT OR IGNORE INTO mandates (id, client_name, objective)
VALUES (1, 'Example Client', 'Build a synthetic QA lead list');

INSERT OR IGNORE INTO leads (
    company_name, domain, contact_name, email, source, fingerprint
) VALUES (
    'Example Company', 'example.test', 'Test Contact',
    'test.contact@example.test', 'synthetic_seed', 'synthetic-example-company'
);

