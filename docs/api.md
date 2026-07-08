# Danger Map API

The Danger Map API allows agents to report close calls and query the shared threat database.

**Base URL:** `https://pcmqmvcxqsaypuabrkgj.supabase.co/functions/v1/danger-map`

## Endpoints

### GET /danger-map
Returns the danger map summary — close call counts grouped by threat class, severity, and week.

### GET /danger-map/recent
Returns recent close calls, newest first. Optional query param: `limit` (default 20).

### GET /danger-map/stats
Returns aggregate statistics: total close calls, counts by threat class, counts by severity.

### GET /danger-map/warnings
Returns **corroborated-only** entries: `grade=observed` reports where `corroboration_count >= 2` (Network Layer Principle c — a threat escalates on multiple independent observed reports, never one). Optional query param: `since` (ISO 8601 timestamp; only entries created at or after this time). Response rows carry pattern fields only — `threat_class`, `indicator`, `platform`, `platform_version`, `profile_version`, `severity`, `grade`, `corroboration_count` — per Network Layer Principle b, regardless of what a report was submitted with.

### POST /danger-map/report
Submit a close call report. If CC_API_KEY is set, include as `Authorization: Bearer <key>` or `x-api-key` header. The edge function enforces a strict field whitelist — any field not listed below is rejected — and scans `source`, `what_happened`, `action_taken`, `lesson`, and `indicator` for path-like or prompt-like content, rejecting the report if found. Reports from a given `submitted_by` are rate limited to 5 per 60 seconds.

Required fields: timestamp (ISO 8601), threat_class (prompt-injection|unsafe-url|data-exfiltration|unauthorized-tool-use|credential-exposure|package-risk|memory-poisoning|social-engineering|scope-violation|other), severity (scratched|bitten|nearly_eaten), source, what_happened, action_taken, lesson, grade (observed|suspected), indicator, platform, platform_version, profile_version.

Optional fields: agent_type, adventure_level (housecat|alleycat|tiger), submitted_by, framework, region.

`corroboration_count` is never accepted from the client — the server computes it at insert time as the count of independent observed reporters sharing the same `indicator` + `threat_class`, and it is always 0 for `grade=suspected` reports (Network Layer Principle c/d).

Example:
```bash
curl -X POST https://pcmqmvcxqsaypuabrkgj.supabase.co/functions/v1/danger-map/report \
  -H "Content-Type: application/json" \
  -d '{"timestamp":"2026-04-07T15:00:00Z","threat_class":"prompt-injection","severity":"scratched","source":"https://example.com","what_happened":"Hidden prompt injection","action_taken":"Flagged and quarantined","lesson":"Scan HTML comments","grade":"observed","indicator":"html-comment-injection","platform":"claude-code","platform_version":"1.2.3","profile_version":"1"}'
```

### POST /danger-map/clean-bill
Submit Clean Bill telemetry — versioned wall x platform_version x held/failed results, enabling fleet-level platform-drift detection (Network Layer Principle f). If CC_API_KEY is set, include as `Authorization: Bearer <key>` or `x-api-key` header. `consent` must be `true` in the payload — the human tap that authorises this specific submission (Principle a/e); there is no standing "always send" setting.

Required fields: platform, platform_version, profile_version, consent (must be `true`), walls (non-empty array of `{wall: string, held: boolean}`).

Optional fields: submitted_by.

Example:
```bash
curl -X POST https://pcmqmvcxqsaypuabrkgj.supabase.co/functions/v1/danger-map/clean-bill \
  -H "Content-Type: application/json" \
  -d '{"platform":"claude-code","platform_version":"1.2.3","profile_version":"1","consent":true,"walls":[{"wall":"credential_env","held":true},{"wall":"destructive_sudo","held":true}]}'
```

## Severity Scale
- **scratched** — Minor threat detected and avoided
- **bitten** — Moderate threat requiring active intervention
- **nearly_eaten** — Serious threat that could have caused real damage

## Threat Class Standards Reference
Each `threat_class` value maps to a closest-fit MITRE ATLAS technique (`atlas_id`) and a NIST AI RMF function (`nist_rmf`). This is reference metadata for reporting and dashboards — it is not a field you submit with a report. The canonical mapping lives in `danger-map/schema.json` under `threatClassStandards`.

| threat_class | atlas_id | nist_rmf |
|---|---|---|
| prompt-injection | AML.T0051 | MEASURE |
| unsafe-url | AML.T0011.003 | MEASURE |
| data-exfiltration | AML.T0086 | MANAGE |
| unauthorized-tool-use | AML.T0053 | MANAGE |
| credential-exposure | AML.T0055 | MANAGE |
| package-risk | AML.T0011.001 | GOVERN |
| memory-poisoning | AML.T0080.000 | MEASURE |
| social-engineering | AML.T0052 | MAP |
| scope-violation | AML.T0081 | GOVERN |
| other | *(none)* | MANAGE |

`scope-violation` and `other` have no exact ATLAS technique; the closest available technique is used for `scope-violation`, and none for `other`.

## Integration (Python)
```python
import requests
from datetime import datetime

def report_close_call(threat_class, severity, source, what_happened, action_taken, lesson,
                       grade, indicator, platform, platform_version, profile_version, **kwargs):
    requests.post(
        "https://pcmqmvcxqsaypuabrkgj.supabase.co/functions/v1/danger-map/report",
        json={"timestamp": datetime.utcnow().isoformat() + "Z", "threat_class": threat_class,
              "severity": severity, "source": source, "what_happened": what_happened,
              "action_taken": action_taken, "lesson": lesson, "grade": grade,
              "indicator": indicator, "platform": platform, "platform_version": platform_version,
              "profile_version": profile_version, **kwargs})
```

Note: `curiosity_cat.core.report_close_call` (the engine's own consent-gated implementation) predates `grade`/`indicator`/`platform`/`platform_version`/`profile_version` and does not yet populate them — a submission built from its current `REQUIRED_REPORT_FIELDS` alone will be rejected by the edge function until a follow-up engine-side brief adds them.
