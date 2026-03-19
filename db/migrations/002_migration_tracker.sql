CREATE TABLE IF NOT EXISTS migrations (
    filename TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ DEFAULT now()
);

-- Record already-applied migrations so they don't run again
INSERT INTO migrations (filename) VALUES ('001_init.sql') 
    ON CONFLICT DO NOTHING;
INSERT INTO migrations (filename) VALUES ('002_migrations_tracker.sql') 
    ON CONFLICT DO NOTHING;
INSERT INTO migrations (filename) VALUES ('003_create_test_table.sql') 
    ON CONFLICT DO NOTHING;