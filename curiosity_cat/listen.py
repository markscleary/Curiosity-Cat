"""curiosity-cat listen — reference Watcher listener.

A local HTTP server that receives the events the PreToolUse/PostToolUse
hooks compile --target claude-code emits (curiosity_cat/events.py): prints
one Meow-voice sentence per event, and queues denied events that carry a
threat_class onto the profile's Mouse Tray via core.queue_close_call().

Reference implementation, not the shipping Feed/Bell (that's the Tauri
shell, APP-4) — this exists so the hook round-trip can be watched and
proven from the CLI alone. Never submits anything to the Danger Map
itself: queuing is the only thing this does (Network Layer Principles a/e).
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import __version__, core
from .events import WATCHER_HOST, WATCHER_PORT


def _profile_manifest(profile_dir):
    manifest_path = Path(profile_dir) / "manifest.json"
    if not manifest_path.exists():
        return {}
    try:
        return json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def meow_line(event):
    """One Meow-voice sentence for a received watcher event — never the
    raw tool_input this event was built from; the event itself already
    carries nothing but a pattern-not-payload digest, so there is nothing
    unsafe to print here.
    """
    tool = event.get("tool", "something")
    verdict = event.get("verdict")
    if verdict == "denied":
        return f"\U0001F431 hackles up — {tool} tried something and the fence said no."
    if verdict == "held":
        return f"\U0001F431 ears up — {tool} is waiting on your say-so."
    return f"\U0001F431 {tool} went by, no trouble."


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

    def do_POST(self):
        if self.path != "/event":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(length) if length else b""
        try:
            event = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            return

        print(meow_line(event))
        sys.stdout.flush()

        if _should_queue(event):
            report = close_call_from_event(event, self.server.profile_dir)
            core.queue_close_call(report, self.server.profile_dir)

        self.send_response(204)
        self.end_headers()


def serve_forever(profile_dir, host=WATCHER_HOST, port=WATCHER_PORT):
    server = ThreadingHTTPServer((host, port), WatcherHandler)
    server.profile_dir = profile_dir
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
