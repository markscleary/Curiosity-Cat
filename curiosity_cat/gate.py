"""curiosity_cat.gate — the PreToolUse approval gate for held (irreversible-
class) actions (docs/app/APP_SPEC.md Watcher section: "approval gate ...
timeout default = deny"). events.py's PreToolUse hook calls
request_decision() only for a "held" verdict — every other verdict that hook
builds is observational, POST-and-move-on. A held one is different: it
needs an actual decision before this hook can honestly answer Claude Code's
permission engine, so this is the one place in the Watcher wiring that
talks back instead of just reporting.

Fails closed throughout — the opposite of the rest of the Watcher's
fail-open discipline. No listener running, a dropped connection, a
malformed reply, or simply no reply before the timeout all resolve to
DECISION_DENY. An approval gate that quietly opened on any hiccup would not
be a gate.
"""

import json
import urllib.request

from .core import WATCHER_HOST, WATCHER_PORT

GATE_URL = f"http://{WATCHER_HOST}:{WATCHER_PORT}/event/hold"

# Kept comfortably under the PreToolUse hook's own compiled timeout
# (core._WATCHER_GATE_TIMEOUT_SECONDS) so a normal timeout-deny round trip
# finishes and reports itself honestly, rather than Claude Code killing the
# hook process first and leaving no decision at all.
DEFAULT_TIMEOUT_SECONDS = 25

DECISION_ALLOW = "allow"
DECISION_DENY = "deny"


def request_decision(event, timeout=DEFAULT_TIMEOUT_SECONDS, url=GATE_URL):
    """POST a held event (a plain jsonable dict) to the Watcher listener's
    approval-gate endpoint and wait up to `timeout` seconds for a human
    decision. Returns DECISION_ALLOW only when the listener explicitly said
    so; every other outcome — connection refused, timeout, malformed
    response, an explicit deny — returns DECISION_DENY.
    """
    data = json.dumps(event).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read())
    except Exception:  # noqa: BLE001 - fail-closed: anything but an explicit allow is a deny
        return DECISION_DENY
    return DECISION_ALLOW if body.get("decision") == DECISION_ALLOW else DECISION_DENY


def hook_output(decision, event):
    """The Claude Code PreToolUse hook JSON contract for a definitive
    allow/deny decision, printed to stdout with exit code 0. `event` is the
    plain jsonable dict (see events.to_jsonable), not the WatcherEvent
    dataclass.
    """
    tool = event.get("tool") or "this tool"
    if decision == DECISION_ALLOW:
        reason = f"Curiosity Cat: the operator approved {tool} from the Feed's approval gate."
    else:
        reason = (f"Curiosity Cat: {tool} is an irreversible-class action held for approval — "
                  "the operator denied it, or didn't answer before the timeout (no response = deny).")
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }
