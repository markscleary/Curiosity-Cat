import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
};

const THREAT_CLASSES = [
  "url", "download", "credential", "injection",
  "package", "execution", "data_leak", "query_leak",
  "source_quality", "other",
] as const;

const SEVERITIES = ["scratched", "bitten", "nearly_eaten"] as const;
const ADVENTURE_LEVELS = ["housecat", "alleycat", "custom"] as const;

const REQUIRED_FIELDS = [
  "timestamp", "threat_class", "severity",
  "source", "what_happened", "action_taken", "lesson",
] as const;

interface CloseCallReport {
  timestamp: string;
  threat_class: string;
  severity: string;
  source: string;
  what_happened: string;
  action_taken: string;
  lesson: string;
  agent_type?: string;
  adventure_level?: string;
  submitted_by?: string;
  framework?: string;
  region?: string;
  confidence_score?: number;
}

interface ValidationError {
  field: string;
  message: string;
}

function validateReport(body: Record<string, unknown>): ValidationError[] {
  const errors: ValidationError[] = [];

  // Check required fields
  for (const field of REQUIRED_FIELDS) {
    if (body[field] === undefined || body[field] === null || body[field] === "") {
      errors.push({ field, message: `${field} is required` });
    }
  }

  // Validate timestamp format
  if (body.timestamp && typeof body.timestamp === "string") {
    const parsed = Date.parse(body.timestamp);
    if (isNaN(parsed)) {
      errors.push({ field: "timestamp", message: "timestamp must be a valid ISO 8601 date-time string" });
    }
  }

  // Validate threat_class enum
  if (body.threat_class !== undefined && !THREAT_CLASSES.includes(body.threat_class as typeof THREAT_CLASSES[number])) {
    errors.push({
      field: "threat_class",
      message: `threat_class must be one of: ${THREAT_CLASSES.join(", ")}`,
    });
  }

  // Validate severity enum
  if (body.severity !== undefined && !SEVERITIES.includes(body.severity as typeof SEVERITIES[number])) {
    errors.push({
      field: "severity",
      message: `severity must be one of: ${SEVERITIES.join(", ")}`,
    });
  }

  // Validate adventure_level enum (optional)
  if (body.adventure_level !== undefined && !ADVENTURE_LEVELS.includes(body.adventure_level as typeof ADVENTURE_LEVELS[number])) {
    errors.push({
      field: "adventure_level",
      message: `adventure_level must be one of: ${ADVENTURE_LEVELS.join(", ")}`,
    });
  }

  // Validate confidence_score range (optional, 0–1)
  if (body.confidence_score !== undefined) {
    const score = Number(body.confidence_score);
    if (isNaN(score) || score < 0 || score > 1) {
      errors.push({
        field: "confidence_score",
        message: "confidence_score must be a number between 0 and 1",
      });
    }
  }

  return errors;
}

Deno.serve(async (req: Request) => {
  // Handle CORS preflight
  if (req.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: CORS_HEADERS });
  }

  // Only allow POST
  if (req.method !== "POST") {
    return new Response(
      JSON.stringify({ error: "Method not allowed" }),
      { status: 405, headers: { ...CORS_HEADERS, "Content-Type": "application/json" } },
    );
  }

  // Parse JSON body
  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return new Response(
      JSON.stringify({ error: "Invalid JSON body" }),
      { status: 400, headers: { ...CORS_HEADERS, "Content-Type": "application/json" } },
    );
  }

  // Validate
  const errors = validateReport(body);
  if (errors.length > 0) {
    return new Response(
      JSON.stringify({ error: "Validation failed", details: errors }),
      { status: 400, headers: { ...CORS_HEADERS, "Content-Type": "application/json" } },
    );
  }

  // Build insert payload (only schema-known fields)
  const report = body as CloseCallReport;
  const insertPayload: Record<string, unknown> = {
    timestamp: report.timestamp,
    threat_class: report.threat_class,
    severity: report.severity,
    source: report.source,
    what_happened: report.what_happened,
    action_taken: report.action_taken,
    lesson: report.lesson,
  };
  if (report.agent_type !== undefined) insertPayload.agent_type = report.agent_type;
  if (report.adventure_level !== undefined) insertPayload.adventure_level = report.adventure_level;
  if (report.submitted_by !== undefined) insertPayload.submitted_by = report.submitted_by;
  if (report.framework !== undefined) insertPayload.framework = report.framework;
  if (report.region !== undefined) insertPayload.region = report.region;

  // Insert into Supabase
  const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
  const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
  const supabase = createClient(supabaseUrl, serviceRoleKey);

  const { data, error } = await supabase
    .from("close_calls")
    .insert(insertPayload)
    .select("id")
    .single();

  if (error) {
    console.error("Insert error:", error);
    return new Response(
      JSON.stringify({ error: "Failed to save report", details: error.message }),
      { status: 500, headers: { ...CORS_HEADERS, "Content-Type": "application/json" } },
    );
  }

  return new Response(
    JSON.stringify({ local_event_id: data.id }),
    { status: 201, headers: { ...CORS_HEADERS, "Content-Type": "application/json" } },
  );
});
