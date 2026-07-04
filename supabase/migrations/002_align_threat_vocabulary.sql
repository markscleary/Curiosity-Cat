-- Align close_calls CHECK constraints with the canonical vocabulary in danger-map/schema.json
-- 001_danger_map.sql shipped with a placeholder threat_class enum and an
-- adventure_level enum missing 'tiger'. This brings both in line with the
-- schema that the edge function, CLI, and docs already validate against.

ALTER TABLE close_calls DROP CONSTRAINT close_calls_threat_class_check;
ALTER TABLE close_calls ADD CONSTRAINT close_calls_threat_class_check CHECK (threat_class IN (
    'prompt-injection', 'unsafe-url', 'data-exfiltration', 'unauthorized-tool-use',
    'credential-exposure', 'package-risk', 'memory-poisoning', 'social-engineering',
    'scope-violation', 'other'
));

ALTER TABLE close_calls DROP CONSTRAINT close_calls_adventure_level_check;
ALTER TABLE close_calls ADD CONSTRAINT close_calls_adventure_level_check CHECK (adventure_level IN (
    'housecat', 'alleycat', 'tiger'
));
