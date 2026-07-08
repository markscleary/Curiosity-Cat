import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization, x-api-key",
};

const THREAT_CLASSES = [
  "prompt-injection", "unsafe-url", "data-exfiltration", "unauthorized-tool-use",
  "credential-exposure", "package-risk", "memory-poisoning", "social-engineering",
  "scope-violation", "other",
];
const SEVERITIES = ["scratched", "bitten", "nearly_eaten"];
const ADVENTURE_LEVELS = ["housecat", "alleycat", "tiger"];
const GRADES = ["observed", "suspected"];

// Pattern not payload (docs/app/APP_SPEC.md, Network Layer Principles b).
// A report is only ever allowed to carry these fields — anything else is
// rejected outright rather than silently dropped, so a caller sending
// unexpected data finds out immediately.
const REQUIRED_REPORT_FIELDS = [
  "timestamp", "threat_class", "severity", "source", "what_happened", "action_taken", "lesson",
  "grade", "indicator", "platform", "platform_version", "profile_version",
];
const OPTIONAL_REPORT_FIELDS = ["agent_type", "adventure_level", "submitted_by", "framework", "region"];
const ALLOWED_REPORT_FIELDS = new Set([...REQUIRED_REPORT_FIELDS, ...OPTIONAL_REPORT_FIELDS]);

// Free-text fields get scanned for path-like or prompt-like content before
// insert. This is a basic heuristic screen, not a guarantee — the schema
// still accepts free text in the legacy fields (source/what_happened/
// action_taken/lesson) pending a future engine-side brief that replaces
// them with `indicator`. Until then, this is the enforcement point.
const FREE_TEXT_FIELDS = ["source", "what_happened", "action_taken", "lesson", "indicator"];
const PATH_LIKE = /(?:[A-Za-z]:\\|\/(?:Users|home|etc|var|tmp|root|Applications)\/|~[\/\\]|\.\.[\/\\]|(?:\/[\w.\-]+){2,})/;
const PROMPT_LIKE = /\n\s*\n|```|\bignore (?:all |any )?(?:previous|prior) instructions\b|\byou are (?:a|an|the)\b|\bsystem prompt\b/i;
const MAX_FREE_TEXT_LENGTH = 400;

const RATE_LIMIT_WINDOW_SECONDS = 60;
const RATE_LIMIT_MAX_REPORTS = 5;

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
  });
}

function checkApiKey(req: Request): boolean {
  const expectedKey = Deno.env.get("CC_API_KEY");
  if (!expectedKey) return true; // no key configured, allow all

  const authHeader = req.headers.get("Authorization");
  if (authHeader?.startsWith("Bearer ")) {
    return authHeader.slice(7) === expectedKey;
  }
  const xApiKey = req.headers.get("x-api-key");
  return xApiKey === expectedKey;
}

function findDisallowedContent(body: Record<string, unknown>): string | null {
  for (const field of FREE_TEXT_FIELDS) {
    const value = body[field];
    if (typeof value !== "string") continue;
    if (value.length > MAX_FREE_TEXT_LENGTH) {
      return `${field} exceeds ${MAX_FREE_TEXT_LENGTH} characters — reports carry patterns, not payloads`;
    }
    if (PATH_LIKE.test(value)) {
      return `${field} looks path-like — reports must never carry file paths`;
    }
    if (PROMPT_LIKE.test(value)) {
      return `${field} looks prompt-like — reports must never carry prompt or file content`;
    }
  }
  return null;
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: CORS_HEADERS });
  }

  const url = new URL(req.url);
  // Path after the function name, e.g. "" | "/recent" | "/stats" | "/report"
  const path = url.pathname.replace(/^\/danger-map/, "").replace(/\/$/, "") || "/";

  const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
  const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
  const supabase = createClient(supabaseUrl, serviceRoleKey);

  // GET / — summary by threat class, severity, and week
  if (req.method === "GET" && path === "/") {
    const { data, error } = await supabase
      .from("danger_map_summary")
      .select("*");

    if (error) return json({ error: error.message }, 500);
    return json({ data });
  }

  // GET /recent — latest close calls
  if (req.method === "GET" && path === "/recent") {
    const limit = Math.min(parseInt(url.searchParams.get("limit") ?? "20"), 100);

    const { data, error } = await supabase
      .from("close_calls")
      .select(
        "id, created_at, timestamp, threat_class, severity, source, what_happened, action_taken, lesson, agent_type, adventure_level, framework, region, grade, indicator, platform, platform_version, profile_version, corroboration_count"
      )
      .order("created_at", { ascending: false })
      .limit(limit);

    if (error) return json({ error: error.message }, 500);
    return json({ data });
  }

  // GET /stats — aggregate counts
  if (req.method === "GET" && path === "/stats") {
    const { count: total, error: countError } = await supabase
      .from("close_calls")
      .select("*", { count: "exact", head: true });

    if (countError) return json({ error: countError.message }, 500);

    const { data: byClass, error: classError } = await supabase
      .from("close_calls")
      .select("threat_class");

    if (classError) return json({ error: classError.message }, 500);

    const { data: bySev, error: sevError } = await supabase
      .from("close_calls")
      .select("severity");

    if (sevError) return json({ error: sevError.message }, 500);

    const byThreatClass: Record<string, number> = {};
    for (const row of byClass ?? []) {
      byThreatClass[row.threat_class] = (byThreatClass[row.threat_class] ?? 0) + 1;
    }

    const bySeverity: Record<string, number> = {};
    for (const row of bySev ?? []) {
      bySeverity[row.severity] = (bySeverity[row.severity] ?? 0) + 1;
    }

    return json({ total, by_threat_class: byThreatClass, by_severity: bySeverity });
  }

  // GET /warnings?since= — corroborated-only entries (Network Layer
  // Principle c: a threat escalates on multiple independent observed
  // reports, never one). Pattern fields only, per Principle b.
  if (req.method === "GET" && path === "/warnings") {
    const since = url.searchParams.get("since");

    let query = supabase
      .from("danger_map_warnings")
      .select("*")
      .order("created_at", { ascending: false });

    if (since) {
      const sinceDate = new Date(since);
      if (isNaN(sinceDate.getTime())) {
        return json({ error: "Invalid `since` — expected an ISO 8601 timestamp" }, 400);
      }
      query = query.gte("created_at", sinceDate.toISOString());
    }

    const { data, error } = await query;
    if (error) return json({ error: error.message }, 500);
    return json({ data });
  }

  // POST /report — submit a close call
  if (req.method === "POST" && path === "/report") {
    if (!checkApiKey(req)) {
      return json({ error: "Unauthorized" }, 401);
    }

    let body: Record<string, unknown>;
    try {
      body = await req.json();
    } catch {
      return json({ error: "Invalid JSON body" }, 400);
    }

    // Strict field whitelist — an unrecognised field is rejected rather
    // than silently dropped or stored.
    const unknownFields = Object.keys(body).filter((k) => !ALLOWED_REPORT_FIELDS.has(k));
    if (unknownFields.length > 0) {
      return json({ error: `Unrecognised field(s): ${unknownFields.join(", ")}` }, 400);
    }

    // Validate required fields
    for (const field of REQUIRED_REPORT_FIELDS) {
      if (!body[field]) {
        return json({ error: `Missing required field: ${field}` }, 400);
      }
    }

    if (!THREAT_CLASSES.includes(body.threat_class as string)) {
      return json({ error: `Invalid threat_class. Must be one of: ${THREAT_CLASSES.join(", ")}` }, 400);
    }

    if (!SEVERITIES.includes(body.severity as string)) {
      return json({ error: `Invalid severity. Must be one of: ${SEVERITIES.join(", ")}` }, 400);
    }

    if (!GRADES.includes(body.grade as string)) {
      return json({ error: `Invalid grade. Must be one of: ${GRADES.join(", ")}` }, 400);
    }

    if (body.adventure_level && !ADVENTURE_LEVELS.includes(body.adventure_level as string)) {
      return json({ error: `Invalid adventure_level. Must be one of: ${ADVENTURE_LEVELS.join(", ")}` }, 400);
    }

    const disallowed = findDisallowedContent(body);
    if (disallowed) {
      return json({ error: disallowed }, 400);
    }

    // Basic rate limiting per reporter hash — can only apply when the
    // reporter identified itself via submitted_by (a hashed operator ID,
    // never PII); anonymous reports aren't individually rate limited.
    const submittedBy = body.submitted_by as string | undefined;
    if (submittedBy) {
      const windowStart = new Date(Date.now() - RATE_LIMIT_WINDOW_SECONDS * 1000).toISOString();
      const { count: recentCount, error: rateLimitError } = await supabase
        .from("close_calls")
        .select("*", { count: "exact", head: true })
        .eq("submitted_by", submittedBy)
        .gte("created_at", windowStart);

      if (rateLimitError) return json({ error: rateLimitError.message }, 500);
      if ((recentCount ?? 0) >= RATE_LIMIT_MAX_REPORTS) {
        return json({ error: "Rate limit exceeded — too many reports from this reporter recently" }, 429);
      }
    }

    // Corroboration count — independent observed reporters sharing this
    // indicator + threat_class, including this submission if it's observed.
    // Never client-supplied (Network Layer Principle c/d).
    let corroborationCount = 0;
    if (body.grade === "observed") {
      const { data: priorReports, error: corroborationError } = await supabase
        .from("close_calls")
        .select("submitted_by")
        .eq("grade", "observed")
        .eq("threat_class", body.threat_class)
        .eq("indicator", body.indicator);

      if (corroborationError) return json({ error: corroborationError.message }, 500);

      const reporters = new Set(
        (priorReports ?? []).map((r) => r.submitted_by).filter((v): v is string => !!v)
      );
      if (submittedBy) reporters.add(submittedBy);
      // If no reporter identified itself (this one included), fall back to
      // a raw report count so corroboration still advances.
      corroborationCount = reporters.size > 0 ? reporters.size : (priorReports ?? []).length + 1;
    }

    const insert = {
      timestamp: body.timestamp,
      threat_class: body.threat_class,
      severity: body.severity,
      source: body.source,
      what_happened: body.what_happened,
      action_taken: body.action_taken,
      lesson: body.lesson,
      agent_type: body.agent_type ?? null,
      adventure_level: body.adventure_level ?? null,
      submitted_by: body.submitted_by ?? null,
      framework: body.framework ?? null,
      region: body.region ?? null,
      grade: body.grade,
      indicator: body.indicator,
      platform: body.platform,
      platform_version: body.platform_version,
      profile_version: body.profile_version,
      corroboration_count: corroborationCount,
    };

    const { data, error } = await supabase
      .from("close_calls")
      .insert(insert)
      .select("id, created_at, corroboration_count")
      .single();

    if (error) return json({ error: error.message }, 500);
    return json({ ok: true, id: data.id, created_at: data.created_at, corroboration_count: data.corroboration_count }, 201);
  }

  // POST /clean-bill — submit Clean Bill telemetry (Network Layer
  // Principle f). Consent is required in the payload itself — the human
  // tap that authorises this specific submission, not a standing setting.
  if (req.method === "POST" && path === "/clean-bill") {
    if (!checkApiKey(req)) {
      return json({ error: "Unauthorized" }, 401);
    }

    let body: Record<string, unknown>;
    try {
      body = await req.json();
    } catch {
      return json({ error: "Invalid JSON body" }, 400);
    }

    if (body.consent !== true) {
      return json({ error: "consent must be true — no silent clean-bill telemetry submission" }, 400);
    }

    for (const field of ["platform", "platform_version", "profile_version", "walls"]) {
      if (!body[field]) {
        return json({ error: `Missing required field: ${field}` }, 400);
      }
    }

    const walls = body.walls;
    if (!Array.isArray(walls) || walls.length === 0) {
      return json({ error: "walls must be a non-empty array of {wall, held}" }, 400);
    }
    for (const w of walls) {
      if (typeof w !== "object" || w === null || typeof w.wall !== "string" || typeof w.held !== "boolean") {
        return json({ error: "each entry in walls must be {wall: string, held: boolean}" }, 400);
      }
    }

    const submittedBy = (body.submitted_by as string | undefined) ?? null;
    const rows = walls.map((w: { wall: string; held: boolean }) => ({
      wall: w.wall,
      held: w.held,
      platform: body.platform,
      platform_version: body.platform_version,
      profile_version: body.profile_version,
      consent: true,
      submitted_by: submittedBy,
    }));

    const { data, error } = await supabase
      .from("clean_bill_telemetry")
      .insert(rows)
      .select("id");

    if (error) return json({ error: error.message }, 500);
    return json({ ok: true, inserted: data.length }, 201);
  }

  return json({ error: "Not found" }, 404);
});
