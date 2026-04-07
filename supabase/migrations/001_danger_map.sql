-- Curiosity Cat Danger Map — Supabase Schema
-- Close call reports from AI agents worldwide

CREATE TABLE IF NOT EXISTS close_calls (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT now(),

    -- Report fields (matches danger-map/schema.json)
    timestamp TIMESTAMPTZ NOT NULL,
    threat_class TEXT NOT NULL CHECK (threat_class IN (
        'url', 'download', 'credential', 'injection',
        'package', 'execution', 'data_leak', 'query_leak',
        'source_quality', 'other'
    )),
    severity TEXT NOT NULL CHECK (severity IN ('scratched', 'bitten', 'nearly_eaten')),
    source TEXT NOT NULL,
    what_happened TEXT NOT NULL,
    action_taken TEXT NOT NULL,
    lesson TEXT NOT NULL,

    -- Optional enrichment
    agent_type TEXT,
    adventure_level TEXT CHECK (adventure_level IN ('housecat', 'alleycat', 'custom')),

    -- Anonymisation metadata
    submitted_by TEXT,  -- hashed operator ID, not PII
    framework TEXT,     -- e.g. 'langchain', 'crewai', 'nanobot', 'custom'
    region TEXT          -- continent-level only: 'MENA', 'APAC', 'EUR', 'NAM', 'LATAM', 'AFR'
);

-- Index for common queries
CREATE INDEX idx_close_calls_threat ON close_calls(threat_class);
CREATE INDEX idx_close_calls_severity ON close_calls(severity);
CREATE INDEX idx_close_calls_created ON close_calls(created_at DESC);

-- Row Level Security
ALTER TABLE close_calls ENABLE ROW LEVEL SECURITY;

-- Anyone can read (anonymised data)
CREATE POLICY "Public read access" ON close_calls
    FOR SELECT USING (true);

-- Only authenticated users can insert
CREATE POLICY "Authenticated insert" ON close_calls
    FOR INSERT WITH CHECK (auth.role() = 'authenticated');

-- Aggregate view for dashboard
CREATE VIEW danger_map_summary AS
SELECT
    threat_class,
    severity,
    COUNT(*) as incident_count,
    DATE_TRUNC('week', created_at) as week
FROM close_calls
GROUP BY threat_class, severity, DATE_TRUNC('week', created_at)
ORDER BY week DESC;
