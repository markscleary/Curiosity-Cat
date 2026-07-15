"""curiosity-cat listen — reference Watcher listener.

A local HTTP server that receives the events the PreToolUse/PostToolUse
hooks compile --target claude-code emits (curiosity_cat/events.py): prints
one Meow-voice line per event (curiosity_cat.meow — the same formatter the
app's Feed window reads through), queues denied events that carry a
threat_class onto the profile's Mouse Tray via core.queue_close_call(), and
answers the approval gate for held (irreversible-class) events.

Reference implementation, not the shipping Feed/Bell (that's the Tauri
shell, APP-4) — but the app's Feed window and the approval gate's native
dialog both talk to *this same* HTTP surface (GET /events, GET
/event/hold/pending, POST /event/hold/<id>/decision): the app just spawns
this listener as its own watcher process instead of reimplementing it.
Never submits anything to the Danger Map itself: queuing is the only thing
this does (Network Layer Principles a/e).
"""

import argparse
import collections
import json
import re
import sys
import threading
import urllib.parse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import __version__, core, meow
from .events import WATCHER_HOST, WATCHER_PORT

# How long a held event waits, server-side, for a human decision before
# this listener answers the gate itself with "deny" (docs/app/APP_SPEC.md
# Watcher section: "timeout default = deny"). Kept under
# gate.DEFAULT_TIMEOUT_SECONDS (the hook's own HTTP client timeout) so this
# listener's own timeout-deny response has time to actually reach the hook,
# rather than the hook's client socket giving up first.
HOLD_WAIT_SECONDS = 20

_DECISION_PATH_RE = re.compile(r"^/event/hold/(\d+)/decision$")

# The Purr's roaming source (curiosity_cat.purr): every event this profile's
# listener has ever received, appended as it arrives. Unlike _EventLog
# above — capped, in-memory, reset whenever this process restarts — this is
# meant to accumulate across restarts and sessions, so a weekly digest has
# something to summarise even if the listener wasn't running continuously.
EVENT_HISTORY_FILENAME = "event-history.jsonl"


def _append_event_history(profile_dir, event):
    """Best-effort append of `event` to this profile's event-history.jsonl.
    Same fail-open discipline as the rest of the Watcher wiring: a write
    failure here (disk full, missing profile_dir, ...) must never break
    event handling.
    """
    try:
        with open(Path(profile_dir) / EVENT_HISTORY_FILENAME, "a") as f:
            f.write(json.dumps(event) + "\n")
    except OSError:
        pass


def _profile_manifest(profile_dir):
    manifest_path = Path(profile_dir) / "manifest.json"
    if not manifest_path.exists():
        return {}
    try:
        return json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def meow_line(event):
    """Back-compat alias for the one-sentence Meow formatter — the shared
    implementation now lives in curiosity_cat.meow so the app Feed can use
    the exact same voice.
    """
    return meow.line(event)


class _EventLog:
    """The Feed's live event stream: every event this listener has seen
    since it started, newest last, capped at `maxlen` so a long-running
    listener doesn't grow without bound. Thread-safe — do_POST/do_GET run
    on separate threads per request (ThreadingHTTPServer).
    """

    def __init__(self, maxlen=500):
        self._lock = threading.Lock()
        self._next_id = 1
        self._entries = collections.deque(maxlen=maxlen)

    def add(self, event, text, kind="event", status=None, lines=None):
        with self._lock:
            entry = {
                "id": self._next_id,
                "received_at": datetime.now(timezone.utc).isoformat(),
                "event": event,
                "meow": text,
                # One string, or three for a denied block — see
                # meow.format_event_lines. Additive to "meow" (the joined
                # text), so the Feed can lay a block out as distinct lines
                # ("what tried / why no / what to do") without the app
                # reimplementing meow.py's wording itself.
                "meow_lines": lines if lines is not None else [text],
                "kind": kind,
                "status": status,
            }
            self._next_id += 1
            self._entries.append(entry)
            return entry

    def update_status(self, entry_id, status):
        with self._lock:
            for entry in self._entries:
                if entry["id"] == entry_id:
                    entry["status"] = status
                    return entry
        return None

    def since(self, after_id):
        with self._lock:
            return [e for e in self._entries if e["id"] > after_id]


class _HoldRegistry:
    """Pending approval-gate decisions, keyed by _EventLog entry id. One
    thread blocks in wait() (the request handling the hook's POST
    /event/hold); a different thread — later, from a different connection
    — calls resolve() once a human answers (POST
    /event/hold/<id>/decision), or wait() simply times out and the caller
    decides what a timeout means (this codebase: deny).
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._pending = {}

    def create(self, entry_id):
        with self._lock:
            self._pending[entry_id] = {"ready": threading.Event(), "decision": None}

    def resolve(self, entry_id, decision):
        with self._lock:
            record = self._pending.get(entry_id)
        if record is None:
            return False
        record["decision"] = decision
        record["ready"].set()
        return True

    def wait(self, entry_id, timeout):
        with self._lock:
            record = self._pending.get(entry_id)
        if record is None:
            return None
        resolved = record["ready"].wait(timeout)
        with self._lock:
            self._pending.pop(entry_id, None)
        return record["decision"] if resolved else None


def close_call_from_event(event, profile_dir):
    """Translate a watcher event into a Mouse Tray report record.

    grade is always "suspected", never "observed": this event came from a
    PreToolUse hook re-deriving a verdict from the compiled settings.json's
    own deny rules — the same pattern-matching prove()'s self-consistency
    trials use — fired before Claude Code's live permission engine made its
    own decision, never from watching that engine directly. Only a real
    observed (live) prove() trial earns "observed" (docs/app/APP_SPEC.md
    Network Layer Principle d).
    """
    manifest = _profile_manifest(profile_dir)
    tool = event.get("tool", "unknown")
    return {
        "timestamp": event.get("ts") or datetime.now(timezone.utc).isoformat(),
        "threat_class": event.get("threat_class") or "other",
        "severity": "scratched",
        "source": f"hook:{tool}",
        "what_happened": f"The {tool} tool was invoked and matched a deny rule in the compiled profile.",
        "action_taken": "compiled profile permission rules denied the call before it executed",
        "lesson": "Automatic hook-derived close call — review before treating as a verified incident.",
        "grade": core.GRADE_SUSPECTED,
        "indicator": f"{tool.lower()}-deny-pattern",
        "platform": "claude-code",
        "platform_version": core._detect_platform_version() or "unknown",
        "profile_version": manifest.get("profile_version") or __version__,
        "adventure_level": manifest.get("level"),
    }


def _should_queue(event):
    # Mirrors APP_SPEC.md Watcher section: "denied events matching threat
    # classes -> queued Danger Map report". Nothing without a threat_class
    # is queued — a bare "denied" with no classification isn't yet a
    # close-call candidate, it's just a wall doing its job.
    return event.get("verdict") == "denied" and bool(event.get("threat_class"))


class WatcherHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # noqa: A002 - matches BaseHTTPRequestHandler's signature
        pass  # the Meow line below is the log; no double noise on top of it

    # --- shared plumbing --------------------------------------------------

    def _event_log(self):
        return self.server.event_log

    def _holds(self):
        return self.server.holds

    def _send_cors_headers(self):
        # Loopback-only, no auth on this socket by design (same trust
        # boundary as the rest of the Watcher wiring) — CORS is wide open
        # here purely so the app's webview (a different origin than
        # 127.0.0.1:8377) can fetch() this listener directly.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_empty(self, status):
        """A status-only response with an explicit Content-Length: 0.

        BaseHTTPRequestHandler defaults to HTTP/1.0 (closes the connection
        after every response) — a response with no Content-Length at all
        makes urllib's client read the body until the connection closes to
        know it's finished, which races the server's own socket teardown
        and can surface as an intermittent ConnectionResetError rather than
        a clean EOF. An explicit length (even zero) makes every response
        here self-terminating, so no caller — this test suite's `_post()`
        helper or the app's real `fetch()` calls alike — needs to guess.
        """
        self.send_response(status)
        self._send_cors_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _read_json_body(self):
        """Read and parse the request body as JSON. Sends a 400 response
        and returns None on any failure — callers just need to check for
        None and return.
        """
        length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(length) if length else b""
        try:
            return json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid JSON body"})
            return None

    # --- POST ---------------------------------------------------------

    def do_POST(self):
        if self.path == "/event":
            self._handle_event()
        elif self.path == "/event/hold":
            self._handle_hold()
        elif _DECISION_PATH_RE.match(self.path):
            self._handle_decision()
        else:
            self._send_json(404, {"error": "not found"})

    def _handle_event(self):
        event = self._read_json_body()
        if event is None:
            return

        text = meow.format_event(event)
        print(text)
        sys.stdout.flush()
        self._event_log().add(
            event, text, kind="event", status=event.get("verdict"), lines=meow.format_event_lines(event)
        )
        _append_event_history(self.server.profile_dir, event)

        if _should_queue(event):
            report = close_call_from_event(event, self.server.profile_dir)
            core.queue_close_call(report, self.server.profile_dir)

        self._send_empty(204)

    def _handle_hold(self):
        """The approval gate's server side: hold this connection open
        until a human answers via /event/hold/<id>/decision, or this
        listener's own timeout elapses — no response, no ambiguity, the
        answer is deny (docs/app/APP_SPEC.md Watcher section).
        """
        event = self._read_json_body()
        if event is None:
            return

        text = meow.line(event)
        print(text)
        print(f"   Approve: curl -s -X POST http://{self.server.server_address[0]}:"
              f"{self.server.server_address[1]}/event/hold/<id>/decision -d '{{\"decision\":\"allow\"}}'")
        print(f"   Deny:    curl -s -X POST http://{self.server.server_address[0]}:"
              f"{self.server.server_address[1]}/event/hold/<id>/decision -d '{{\"decision\":\"deny\"}}'")
        sys.stdout.flush()

        entry = self._event_log().add(event, text, kind="hold", status="pending")
        self._holds().create(entry["id"])
        print(f"   (id {entry['id']}, auto-denies in {HOLD_WAIT_SECONDS}s if you do nothing)")
        sys.stdout.flush()

        decision = self._holds().wait(entry["id"], timeout=HOLD_WAIT_SECONDS)
        if decision not in ("allow", "deny"):
            decision = "deny"
        self._event_log().update_status(entry["id"], "allowed" if decision == "allow" else "denied")

        self._send_json(200, {"id": entry["id"], "decision": decision})

    def _handle_decision(self):
        match = _DECISION_PATH_RE.match(self.path)
        entry_id = int(match.group(1))
        body = self._read_json_body()
        if body is None:
            return
        decision = body.get("decision")
        if decision not in ("allow", "deny"):
            self._send_json(400, {"error": 'decision must be "allow" or "deny"'})
            return

        ok = self._holds().resolve(entry_id, decision)
        self._send_empty(204 if ok else 404)

    # --- GET ------------------------------------------------------------

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path == "/events":
            since = 0
            params = urllib.parse.parse_qs(parsed.query)
            if "since" in params:
                try:
                    since = int(params["since"][0])
                except ValueError:
                    since = 0
            self._send_json(200, self._event_log().since(since))
        elif parsed.path == "/event/hold/pending":
            pending = [e for e in self._event_log().since(0) if e["status"] == "pending"]
            self._send_json(200, pending)
        else:
            self._send_json(404, {"error": "not found"})

    def do_OPTIONS(self):
        # CORS preflight — the app webview's fetch() of a JSON POST body
        # (the decision endpoint) triggers one.
        self._send_empty(204)


def serve_forever(profile_dir, host=WATCHER_HOST, port=WATCHER_PORT):
    server = ThreadingHTTPServer((host, port), WatcherHandler)
    server.profile_dir = profile_dir
    server.event_log = _EventLog()
    server.holds = _HoldRegistry()
    print(f"\n\U0001F431 Curiosity Cat is watching — listening on http://{host}:{port}/event\n")
    sys.stdout.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main(argv=None):
    parser = argparse.ArgumentParser(prog="curiosity-cat listen", description="Reference Watcher listener")
    parser.add_argument("--profile", required=True, help="A directory produced by curiosity-cat compile")
    parser.add_argument("--host", default=WATCHER_HOST)
    parser.add_argument("--port", type=int, default=WATCHER_PORT)
    args = parser.parse_args(argv)
    serve_forever(args.profile, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
