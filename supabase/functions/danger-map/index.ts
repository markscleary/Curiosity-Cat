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
        "id, created_at, timestamp, threat_class, severity, source, what_happened, action_taken, lesson, agent_type, adventure_level, framework, region"
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

    // Validate required fields
    const required = ["timestamp", "threat_class", "severity", "source", "what_happened", "action_taken", "lesson"];
    for (const field of required) {
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

    if (body.adventure_level && !ADVENTURE_LEVELS.includes(body.adventure_level as string)) {
      return json({ error: `Invalid adventure_level. Must be one of: ${ADVENTURE_LEVELS.join(", ")}` }, 400);
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
    };

    const { data, error } = await supabase
      .from("close_calls")
      .insert(insert)
      .select("id, created_at")
      .single();

    if (error) return json({ error: error.message }, 500);
    return json({ ok: true, id: data.id, created_at: data.created_at }, 201);
  }

  return json({ error: "Not found" }, 404);
});
