"""curiosity-cat-mcp — Curiosity Cat as an MCP server.

Exposes exactly two tools over stdio, using the official `mcp` Python SDK:

`check`  — a read-only Danger Map lookup (core.check). Never requires
consent: a lookup is not itself a threat finding, and nothing leaves the
machine to perform one beyond the GET the lookup already is.

`report` — files a close call via the existing consent-gated path
(core.report_close_call). docs/app/APP_SPEC.md Network Layer Principle a
requires an explicit human tap before anything leaves the machine; Principle
e requires the operator to have explicitly seen and approved a report before
it goes out. This server treats the MCP tool call itself as that tap: MCP
clients (Claude Code, Claude Desktop, ...) surface a tool call for approval
before it executes, so the approval the operator already gives at the
client level *is* the explicit consent act — there is no second, separate
confirmation step inside this tool. That is a deliberate difference from the
Mouse Tray flow (core.queue_close_call / submit_approved), which exists for
events the Watcher captures automatically with no human present at capture
time, and therefore need a later, separate review step this tool doesn't.
"""

import json
from datetime import datetime, timezone
from typing import Annotated, Literal, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from . import __version__, core

SERVER_NAME = "curiosity-cat"

SERVER_INSTRUCTIONS = (
    "I'm Curiosity Cat \U0001F431 — a safety framework for AI agents, here as two whiskers "
    "for whatever's holding this conversation. Ask me to `check` a URL, package, or command "
    "before you touch it, and I'll tell you if another cat already got scratched there — a "
    "miss means not found, never known safe. If something bites, `report` it — that tool "
    "call is your explicit go-ahead, nothing reaches the Danger Map any other way."
)

mcp = FastMCP(name=SERVER_NAME, instructions=SERVER_INSTRUCTIONS)

_THREAT_CLASSES = [
    "prompt-injection", "unsafe-url", "data-exfiltration", "unauthorized-tool-use",
    "credential-exposure", "package-risk", "memory-poisoning", "social-engineering",
    "scope-violation", "other",
]


def _threat_class_standards():
    """threat_class -> {atlas_id, nist_rmf}, from the bundled Danger Map
    schema's threatClassStandards cross-reference (see docs/api.md).
    """
    schema = json.loads((core.DATA_DIR / "danger-map" / "schema.json").read_text())
    return schema.get("threatClassStandards", {})


def _atlas_references(threat_classes, standards):
    return [
        {"threat_class": tc, "atlas_id": standards.get(tc, {}).get("atlas_id"),
         "nist_rmf": standards.get(tc, {}).get("nist_rmf")}
        for tc in threat_classes
    ]


def _check_sentence(candidate, verdict, threat_classes):
    if not verdict.matched:
        return (f"\U0001F431 whiskers still — no Danger Map match for `{candidate}` right now "
                "(a miss means not found in what we could fetch, not known safe).")
    count = len(verdict.matches)
    incident_word = "incident" if count == 1 else "incidents"
    if threat_classes:
        return (f"\U0001F431 whiskers up — `{candidate}` matches {count} Danger Map {incident_word} "
                f"tagged {', '.join(threat_classes)}.")
    return f"\U0001F431 whiskers up — `{candidate}` matches {count} Danger Map {incident_word}."


@mcp.tool(
    name="check",
    description=(
        "Whisker-check a URL, domain, package name, or command against the Danger Map's "
        "recent close calls before touching it. Read-only, no consent required. Returns "
        "the match verdict, any threat_class(es) involved with their MITRE ATLAS technique "
        "and NIST AI RMF cross-reference, and one human sentence summarising the result."
    ),
)
def check(
    candidate: Annotated[str, Field(
        description="A URL, domain, package name, or command to look up against the Danger Map.",
        min_length=1,
    )],
) -> dict:
    verdict = core.check(candidate)
    standards = _threat_class_standards()
    threat_classes = sorted({m.get("threat_class") for m in verdict.matches if m.get("threat_class")})
    return {
        "candidate": verdict.candidate,
        "checked_at": verdict.checked_at,
        "matched": verdict.matched,
        "matches": verdict.matches,
        "note": verdict.note,
        "threat_classes": threat_classes,
        "atlas_references": _atlas_references(threat_classes, standards),
        "sentence": _check_sentence(candidate, verdict, threat_classes),
    }


@mcp.tool(
    name="report",
    description=(
        "File a close call with the Danger Map. Calling this tool IS the explicit human "
        "consent act Network Layer Principle a requires — the report goes out the moment "
        "this call executes, nothing is queued for a separate later approval. Only call "
        "this when a human operator has actually asked for this close call to be reported; "
        "never invoke it speculatively, automatically, or on the agent's own initiative. "
        "Carries pattern only (threat_class, indicator, platform, profile_version, ...) — "
        "never a raw prompt, file path, or file content."
    ),
)
def report(
    threat_class: Annotated[Literal[tuple(_THREAT_CLASSES)], Field(
        description="Category of threat detected.")],
    severity: Annotated[Literal["scratched", "bitten", "nearly_eaten"], Field(
        description="How close the call was.")],
    source: Annotated[str, Field(
        description="Where the threat came from — a URL, filename, or short description. Never raw file content.")],
    what_happened: Annotated[str, Field(description="One-sentence description of the incident.")],
    action_taken: Annotated[str, Field(description="What the agent did in response.")],
    lesson: Annotated[str, Field(description="One-sentence takeaway.")],
    grade: Annotated[Literal["observed", "suspected"], Field(
        description="observed: a real wall was tested and held/failed against this threat. "
                     "suspected: pattern-matched or inferred, no live wall behind it. State it "
                     "honestly — never inferred or defaulted (Network Layer Principle d).")],
    indicator: Annotated[str, Field(
        description="A normalised threat pattern — a domain, package name, or technique id. "
                     "Never a raw path, prompt, or file content.")],
    platform: Annotated[str, Field(description="Agent platform/runtime, e.g. claude-code.")],
    platform_version: Annotated[str, Field(description="Version of that platform/runtime.")],
    profile_version: Annotated[str, Field(
        default=__version__,
        description="Version of the compiled Danger Map profile in effect. Defaults to this "
                     "server's own curiosity-cat version if the caller doesn't have a compiled "
                     "profile to cite.")] = __version__,
    agent_type: Annotated[Optional[str], Field(
        default=None, description="Type of agent that reported: research, coding, enterprise, general.")] = None,
    adventure_level: Annotated[Optional[Literal["housecat", "alleycat", "tiger"]], Field(
        default=None, description="Operator's adventure slider setting at time of incident.")] = None,
    submitted_by: Annotated[Optional[str], Field(default=None, description="Reporter identifier, optional.")] = None,
    framework: Annotated[Optional[str], Field(
        default=None, description="Agent framework used, e.g. claude-code, langgraph.")] = None,
    region: Annotated[Optional[str], Field(default=None, description="AWS/GCP/Azure region, or 'local'.")] = None,
    timestamp: Annotated[Optional[str], Field(
        default=None, description="ISO 8601 timestamp of the incident. Defaults to now (UTC) if omitted — "
                                   "this tool call is itself the moment of report.")] = None,
    api_key: Annotated[Optional[str], Field(
        default=None, description="Danger Map API key, if this deployment requires one.")] = None,
) -> dict:
    event = {
        "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
        "threat_class": threat_class,
        "severity": severity,
        "source": source,
        "what_happened": what_happened,
        "action_taken": action_taken,
        "lesson": lesson,
        "grade": grade,
        "indicator": indicator,
        "platform": platform,
        "platform_version": platform_version,
        "profile_version": profile_version,
    }
    for key, value in (("agent_type", agent_type), ("adventure_level", adventure_level),
                        ("submitted_by", submitted_by), ("framework", framework), ("region", region)):
        if value is not None:
            event[key] = value

    return core.report_close_call(event, consent=True, api_key=api_key)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
