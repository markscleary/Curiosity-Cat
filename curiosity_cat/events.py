"""curiosity_cat.events — the Watcher's event schema and hook entrypoint.

compile --target claude-code embeds PreToolUse/PostToolUse hook entries into
the compiled settings.json (see core.emit_claude_code_settings) that invoke
this module as `python3 -m curiosity_cat.events <PreToolUse|PostToolUse>`.
This module defines the fixed event shape those hooks POST to the local
Watcher listener at WATCHER_EVENT_URL, and is the hook process itself: read
one hook payload from stdin, build an event, POST it, always exit 0.

Fail-open by design (APP_SPEC.md Watcher section): a listener that's down,
slow, or absent must never surface an error to Claude Code or delay the
tool call being reported on. Every failure mode here is swallowed silently.
"""

import hashlib
import json
import re
import sys
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from . import core, gate

WATCHER_EVENT_URL = "http://127.0.0.1:8377/event"
WATCHER_HOST = "127.0.0.1"
WATCHER_PORT = 8377
WATCHER_TIMEOUT_SECONDS = 1

VERDICT_ALLOWED = "allowed"
VERDICT_DENIED = "denied"
# The approval gate (PreToolUse hold-for-consent on irreversible-class
# actions, APP_SPEC.md Watcher section, curiosity_cat.gate) — see
# _pretool_verdict/_matches_irreversible_bash below for what earns this.
VERDICT_HELD = "held"
VERDICTS = [VERDICT_ALLOWED, VERDICT_DENIED, VERDICT_HELD]

INPUT_DIGEST_SAFE_CHARS = 60

_NETWORK_BASH_PATTERNS = ("Bash(curl:*)", "Bash(wget:*)")


@dataclass
class WatcherEvent:
    """One PreToolUse/PostToolUse observation — APP_SPEC.md Watcher section's
    event schema. `input_digest` is pattern-not-payload (Network Layer
    Principle b): never a full path, prompt, or file content, only a short
    hash plus a bounded, sanitised excerpt (see build_input_digest).
    """

    ts: str
    session: str
    tool: str
    input_digest: str
    verdict: str
    profile_id: Optional[str] = None
    threat_class: Optional[str] = None


def to_jsonable(event):
    return asdict(event) if isinstance(event, WatcherEvent) else event


def _safe_fields(tool_name, tool_input):
    """A pattern-only view of tool_input, safe to hash-and-excerpt: which
    argument keys were present, plus (Bash only) the command's leading verb
    — the same granularity Bash(<verb>:*) deny/ask rules already match on.
    Never a value from file_path, content, command arguments, url, prompt,
    or any other field that could carry a real path, secret, or prompt.
    """
    if not isinstance(tool_input, dict):
        return {}
    fields = {"keys": sorted(tool_input.keys())}
    if tool_name == "Bash" and isinstance(tool_input.get("command"), str):
        verb = tool_input["command"].strip().split(" ", 1)[0]
        if verb:
            fields["verb"] = verb
    return fields


def build_input_digest(tool_name, tool_input):
    """short-hash:safe-excerpt — the hash covers the full (possibly
    sensitive) tool_input for correlation purposes only, one-way and never
    reversible to the original path/prompt/content; the excerpt is built
    exclusively from _safe_fields, so it structurally cannot contain a full
    path or prompt no matter what tool_input holds.
    """
    raw = json.dumps(tool_input, sort_keys=True, default=str) if tool_input else ""
    digest_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]
    excerpt = json.dumps(_safe_fields(tool_name, tool_input), sort_keys=True)
    return f"{digest_hash}:{excerpt[:INPUT_DIGEST_SAFE_CHARS]}"


def _load_permissions(settings_path):
    if not settings_path:
        return None
    try:
        data = json.loads(Path(settings_path).read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return data.get("permissions", {})


def _bash_threat_class(pattern):
    if pattern in core.DESTRUCTIVE_DENY_PATTERNS:
        return "unauthorized-tool-use"
    if pattern in _NETWORK_BASH_PATTERNS:
        return "unsafe-url"
    return "scope-violation"


def _matches_irreversible_bash(command):
    """Would this command match one of core.IRREVERSIBLE_HOLD_PATTERNS —
    the approval gate's floor list of irreversible-class actions? Mirrors
    core._bash_verdict's own prefix-match style.
    """
    for pattern in core.IRREVERSIBLE_HOLD_PATTERNS:
        m = re.match(r"^Bash\((.+):\*\)$", pattern)
        if m and command.strip().startswith(m.group(1)):
            return True
    return False


def _pretool_verdict(tool_name, tool_input, settings_path):
    """The verdict a PreToolUse hook can honestly claim: whether tool_input
    matches a deny pattern in the settings.json this session is actually
    running under, re-derived with the identical logic prove()'s
    self-consistency trials use (core._path_verdict / core._bash_verdict).

    This fires *before* Claude Code's own permission engine reaches its
    decision (PreToolUse always runs first — see docs/app/APP_SPEC.md), so
    it is a live pattern-match prediction, not an observation of that
    engine's actual decision. Never claim more than that: callers that
    queue this onto the Mouse Tray must grade it "suspected", never
    "observed" (Network Layer Principle d).

    Falls back to (allowed, None) for any tool/shape neither helper can
    evaluate (WebFetch, Grep, an unreadable settings file, ...) — same
    "never fabricate a denial" discipline as the rest of this codebase.

    An irreversible-class Bash command (core.IRREVERSIBLE_HOLD_PATTERNS)
    always returns "held", checked before anything else and regardless of
    whether settings_path is even readable: unlike deny/allow, "held" isn't
    derived from the compiled settings.json (Claude Code's permissions
    schema has no bucket for it) — the approval gate (curiosity_cat.gate)
    is this codebase's only enforcement of it.
    """
    if tool_name == "Bash" and isinstance(tool_input.get("command"), str):
        if _matches_irreversible_bash(tool_input["command"]):
            return VERDICT_HELD, None

    perms = _load_permissions(settings_path)
    if perms is None:
        return VERDICT_ALLOWED, None

    if tool_name in ("Read", "Write", "Edit") and isinstance(tool_input.get("file_path"), str):
        observed, pattern = core._path_verdict(perms, tool_name, tool_input["file_path"])
        if observed == "denied":
            threat_class = "credential-exposure" if pattern in core.CREDENTIAL_DENY_PATTERNS else "scope-violation"
            return VERDICT_DENIED, threat_class
        return VERDICT_ALLOWED, None

    if tool_name == "Bash" and isinstance(tool_input.get("command"), str):
        observed, pattern = core._bash_verdict(perms, tool_input["command"])
        if observed == "denied":
            return VERDICT_DENIED, _bash_threat_class(pattern)
        return VERDICT_ALLOWED, None

    return VERDICT_ALLOWED, None


def build_event(hook_event_name, payload, settings_path=None, profile_id=None):
    """Build a WatcherEvent from one already-parsed Claude Code hook stdin
    payload. Never raises: any missing/malformed field degenerates to a
    safe default rather than crashing the hook process.
    """
    tool_name = payload.get("tool_name") or "unknown"
    tool_input = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    session = payload.get("session_id") or "unknown"

    if hook_event_name == "PostToolUse":
        # PostToolUse only ever fires once a tool call has already
        # succeeded — there is no live-denial case to detect here.
        verdict, threat_class = VERDICT_ALLOWED, None
    else:
        verdict, threat_class = _pretool_verdict(tool_name, tool_input, settings_path)

    return WatcherEvent(
        ts=datetime.now(timezone.utc).isoformat(),
        session=session,
        tool=tool_name,
        input_digest=build_input_digest(tool_name, tool_input),
        verdict=verdict,
        profile_id=profile_id,
        threat_class=threat_class,
    )


def post_event(event, url=WATCHER_EVENT_URL, timeout=WATCHER_TIMEOUT_SECONDS):
    """POST event to the Watcher listener. Fail-open by policy: a listener
    that's down, slow, or unreachable must never surface an error to Claude
    Code or delay the tool call being reported on, so *every* exception
    here — connection refused, timeout, DNS, malformed response, whatever —
    is swallowed rather than re-raised. Returns True/False only so tests
    can observe the outcome; real callers (the hook CLI below) ignore it.
    """
    data = json.dumps(to_jsonable(event)).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout):
            pass
        return True
    except Exception:  # noqa: BLE001 - fail-open is the whole point; see docstring
        return False


def _parse_hook_args(argv):
    hook_event_name = argv[0] if argv else "PreToolUse"
    settings_path = None
    profile_id = None
    it = iter(argv[1:])
    for arg in it:
        if arg == "--settings":
            settings_path = next(it, None)
        elif arg == "--profile-id":
            profile_id = next(it, None)
    return hook_event_name, settings_path, profile_id


def main(argv=None):
    """`python3 -m curiosity_cat.events <PreToolUse|PostToolUse> [--settings PATH] [--profile-id ID]`

    This *is* the hook command compile --target claude-code writes into
    settings.json. Reads one hook JSON payload from stdin, builds and posts
    a WatcherEvent, and always returns 0 — a Watcher hook that could ever
    exit nonzero or hang would violate the fail-open contract (APP_SPEC.md
    Watcher section): Claude Code must never notice this hook exists,
    whether the listener is up or not.

    The one exception is a held PreToolUse verdict (the approval gate,
    curiosity_cat.gate): there, this hook's own stdout *is* Claude Code's
    permission decision, printed as the hookSpecificOutput JSON contract,
    and that path fails closed (no listener/no reply/any error -> deny)
    rather than open, by design — see gate.py's docstring.
    """
    argv = sys.argv[1:] if argv is None else argv
    hook_event_name, settings_path, profile_id = _parse_hook_args(argv)

    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:  # noqa: BLE001 - fail-open
        payload = {}

    try:
        event = build_event(hook_event_name, payload, settings_path=settings_path, profile_id=profile_id)
    except Exception:  # noqa: BLE001 - fail-open
        return 0

    if hook_event_name == "PreToolUse" and event.verdict == VERDICT_HELD:
        event_dict = to_jsonable(event)
        try:
            decision = gate.request_decision(event_dict)
        except Exception:  # noqa: BLE001 - fail-closed for the gate specifically, see gate.py
            decision = gate.DECISION_DENY
        print(json.dumps(gate.hook_output(decision, event_dict)))
        try:
            post_event(event)
        except Exception:  # noqa: BLE001 - fail-open
            pass
        return 0

    try:
        post_event(event)
    except Exception:  # noqa: BLE001 - fail-open
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
