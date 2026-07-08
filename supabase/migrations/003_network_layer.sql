-- Network Layer Principles (docs/app/APP_SPEC.md) — schema support for
-- corroboration-gated warnings and versioned Clean Bill telemetry.

-- Report grade: observed vs suspected, distinct end to end (principle d).
-- Existing rows predate the field; backfilled as 'observed' since every
-- report accepted so far came from a real held/failed wall trial, not a
-- pattern-matched inference.
ALTER TABLE close_calls ADD COLUMN grade TEXT NOT NULL DEFAULT 'observed'
    CHECK (grade IN ('observed', 'suspected'));
ALTER TABLE close_calls ALTER COLUMN grade DROP DEFAULT;

-- Pattern, not payload (principle b): the normalised indicator new reports
-- corroborate against, plus the platform/profile provenance needed for
-- fleet-level drift detection.
ALTER TABLE close_calls ADD COLUMN indicator TEXT;
ALTER TABLE close_calls ADD COLUMN platform TEXT;
ALTER TABLE close_calls ADD COLUMN platform_version TEXT;
ALTER TABLE close_calls ADD COLUMN profile_version TEXT;

-- Corroboration before escalation (principle c): count of independent
-- observed reporters sharing this indicator + threat_class, snapshotted by
-- the edge function at insert time. Never client-supplied.
ALTER TABLE close_calls ADD COLUMN corroboration_count INTEGER NOT NULL DEFAULT 0;

CREATE INDEX idx_close_calls_indicator ON close_calls(threat_class, indicator)
    WHERE grade = 'observed';

-- Corroborated-only view backing GET /danger-map/warnings — pattern-only
-- fields, per principle b, regardless of what the write side still accepts.
CREATE VIEW danger_map_warnings AS
SELECT
    id,
    created_at,
    threat_class,
    indicator,
    platform,
    platform_version,
    profile_version,
    severity,
    grade,
    corroboration_count
FROM close_calls
WHERE grade = 'observed' AND corroboration_count >= 2
ORDER BY created_at DESC;

-- Clean Bill telemetry (principle f): one row per wall result per submission.
-- wall x platform_version x held/failed, aggregated across the fleet, is
-- what surfaces platform drift — a wall quietly failing everywhere on one
-- platform version is a signal, not noise.
CREATE TABLE IF NOT EXISTS clean_bill_telemetry (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT now(),

    wall TEXT NOT NULL,
    held BOOLEAN NOT NULL,
    platform TEXT NOT NULL,
    platform_version TEXT NOT NULL,
    profile_version TEXT NOT NULL,

    -- The human tap this row exists because of (principle a/e). Rows are
    -- only ever inserted after the edge function has verified consent=true
    -- on the submission payload; the column records that fact per row.
    consent BOOLEAN NOT NULL CHECK (consent = true),

    submitted_by TEXT  -- hashed operator ID, not PII; same convention as close_calls
);

CREATE INDEX idx_clean_bill_telemetry_wall ON clean_bill_telemetry(wall, platform_version);
CREATE INDEX idx_clean_bill_telemetry_created ON clean_bill_telemetry(created_at DESC);

ALTER TABLE clean_bill_telemetry ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read access" ON clean_bill_telemetry
    FOR SELECT USING (true);

CREATE POLICY "Authenticated insert" ON clean_bill_telemetry
    FOR INSERT WITH CHECK (auth.role() = 'authenticated');

-- Fleet-level platform-drift view: held/failed counts per wall per
-- platform_version per week.
CREATE VIEW clean_bill_drift_summary AS
SELECT
    wall,
    platform,
    platform_version,
    held,
    COUNT(*) as result_count,
    DATE_TRUNC('week', created_at) as week
FROM clean_bill_telemetry
GROUP BY wall, platform, platform_version, held, DATE_TRUNC('week', created_at)
ORDER BY week DESC;
