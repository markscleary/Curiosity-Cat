"""Tests for the reference Watcher listener (curiosity_cat.listen)."""

import json
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from curiosity_cat import core, listen


def _compiled_profile(tmp_path):
    return core.compile_profile("housecat", "claude-code", cwd=tmp_path)


def test_meow_line_denied_says_hackles_up():
    line = listen.meow_line({"tool": "Bash", "verdict": "denied"})
    assert "hackles up" in line
    assert "Bash" in line


def test_meow_line_allowed_says_no_trouble():
    line = listen.meow_line({"tool": "Read", "verdict": "allowed"})
    assert "no trouble" in line
    assert "Read" in line


def test_meow_line_held_says_waiting():
    line = listen.meow_line({"tool": "Write", "verdict": "held"})
    assert "waiting" in line


def test_should_queue_only_denied_with_threat_class():
    assert listen._should_queue({"verdict": "denied", "threat_class": "credential-exposure"}) is True
    assert listen._should_queue({"verdict": "denied"}) is False
    assert listen._should_queue({"verdict": "allowed", "threat_class": "credential-exposure"}) is False
    assert listen._should_queue({"verdict": "allowed"}) is False


def test_close_call_from_event_grades_suspected_never_observed(tmp_path):
    profile = _compiled_profile(tmp_path)
    event = {
        "ts": "2026-07-10T00:00:00+00:00", "session": "s1", "tool": "Bash",
        "input_digest": "abc12345:{}", "verdict": "denied", "threat_class": "unauthorized-tool-use",
        "profile_id": "housecat",
    }
    report = listen.close_call_from_event(event, profile.path)

    assert report["grade"] == core.GRADE_SUSPECTED
    assert report["threat_class"] == "unauthorized-tool-use"
    assert report["platform"] == "claude-code"
    assert report["profile_version"] == core.__version__
    assert report["adventure_level"] == "housecat"
    # Pattern, not payload: never the raw digest or any path/content.
    assert "id_rsa" not in json.dumps(report)


def test_close_call_from_event_satisfies_required_report_fields(tmp_path):
    profile = _compiled_profile(tmp_path)
    event = {
        "ts": "2026-07-10T00:00:00+00:00", "session": "s1", "tool": "Read",
        "input_digest": "abc12345:{}", "verdict": "denied", "threat_class": "credential-exposure",
        "profile_id": "housecat",
    }
    report = listen.close_call_from_event(event, profile.path)
    missing = [f for f in core.REQUIRED_REPORT_FIELDS if not report.get(f)]
    assert missing == []


def test_denied_event_with_threat_class_is_queued_to_mouse_tray(tmp_path):
    profile = _compiled_profile(tmp_path)
    event = {
        "ts": "2026-07-10T00:00:00+00:00", "session": "s1", "tool": "Bash",
        "input_digest": "abc12345:{}", "verdict": "denied", "threat_class": "unauthorized-tool-use",
        "profile_id": "housecat",
    }

    assert listen._should_queue(event)
    report = listen.close_call_from_event(event, profile.path)
    record = core.queue_close_call(report, profile.path)

    queue = core.list_tray(profile.path)
    assert len(queue) == 1
    assert queue[0]["id"] == record["id"]
    assert queue[0]["status"] == "pending"
    assert queue[0]["event"]["grade"] == core.GRADE_SUSPECTED


def test_allowed_event_is_never_queued(tmp_path):
    profile = _compiled_profile(tmp_path)
    event = {
        "ts": "2026-07-10T00:00:00+00:00", "session": "s1", "tool": "Read",
        "input_digest": "abc12345:{}", "verdict": "allowed", "profile_id": "housecat",
    }
    assert not listen._should_queue(event)
    assert core.list_tray(profile.path) == []


@pytest.fixture
def running_listener(tmp_path):
    """A real ThreadingHTTPServer bound to an ephemeral loopback port,
    running curiosity_cat.listen's actual request handler — not the
    fixed Watcher port (8377), so this never collides with a real listener
    that might already be running on the machine.
    """
    profile = _compiled_profile(tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), listen.WatcherHandler)
    server.profile_dir = profile.path
    server.event_log = listen._EventLog()
    server.holds = listen._HoldRegistry()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, profile
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _post(server, path, payload, timeout=5):
    host, port = server.server_address
    data = json.dumps(payload).encode("utf-8") if payload is not None else b"not json"
    request = urllib.request.Request(f"http://{host}:{port}{path}", data=data, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            return response.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        body = None
        if raw:
            try:
                body = json.loads(raw)
            except json.JSONDecodeError:
                body = None
        return exc.code, body


def _get(server, path):
    host, port = server.server_address
    request = urllib.request.Request(f"http://{host}:{port}{path}", method="GET")
    with urllib.request.urlopen(request, timeout=5) as response:
        return response.status, json.loads(response.read())


def test_listener_queues_denied_event_to_mouse_tray_over_real_http(running_listener):
    server, profile = running_listener
    event = {
        "ts": "2026-07-10T00:00:00+00:00", "session": "s1", "tool": "Bash",
        "input_digest": "abc12345:{}", "verdict": "denied", "threat_class": "unauthorized-tool-use",
        "profile_id": "housecat",
    }
    status, _ = _post(server, "/event", event)
    assert status == 204

    queue = core.list_tray(profile.path)
    assert len(queue) == 1
    assert queue[0]["event"]["grade"] == core.GRADE_SUSPECTED
    assert queue[0]["event"]["threat_class"] == "unauthorized-tool-use"


def test_listener_does_not_queue_allowed_event_over_real_http(running_listener):
    server, profile = running_listener
    event = {
        "ts": "2026-07-10T00:00:00+00:00", "session": "s1", "tool": "Read",
        "input_digest": "abc12345:{}", "verdict": "allowed", "profile_id": "housecat",
    }
    status, _ = _post(server, "/event", event)
    assert status == 204
    assert core.list_tray(profile.path) == []


def test_listener_rejects_unknown_path(running_listener):
    server, _profile = running_listener
    status, _ = _post(server, "/not-event", {"tool": "Bash", "verdict": "allowed"})
    assert status == 404


def test_listener_rejects_malformed_json(running_listener):
    server, _profile = running_listener
    status, _ = _post(server, "/event", None)
    assert status == 400


def test_denied_event_prints_meow_block_not_one_liner(running_listener, capsys):
    server, _profile = running_listener
    event = {
        "ts": "2026-07-10T00:00:00+00:00", "session": "s1", "tool": "Bash",
        "input_digest": "abc12345:{}", "verdict": "denied", "threat_class": "unauthorized-tool-use",
        "profile_id": "housecat",
    }
    status, _ = _post(server, "/event", event)
    assert status == 204
    # ThreadingHTTPServer prints from a worker thread; give it a beat.
    time.sleep(0.2)
    printed = capsys.readouterr().out
    assert printed.count(".") >= 3
    assert "disagree" in printed


def test_get_events_returns_recent_events_and_supports_since(running_listener):
    server, _profile = running_listener
    event = {
        "ts": "2026-07-10T00:00:00+00:00", "session": "s1", "tool": "Read",
        "input_digest": "abc12345:{}", "verdict": "allowed", "profile_id": "housecat",
    }
    _post(server, "/event", event)
    status, entries = _get(server, "/events")
    assert status == 200
    assert len(entries) == 1
    assert entries[0]["event"]["tool"] == "Read"
    assert entries[0]["kind"] == "event"

    status, entries_since = _get(server, f"/events?since={entries[0]['id']}")
    assert status == 200
    assert entries_since == []


def test_get_events_includes_meow_lines_split_for_denied_blocks(running_listener):
    server, _profile = running_listener
    allowed = {
        "ts": "2026-07-10T00:00:00+00:00", "session": "s1", "tool": "Read",
        "input_digest": "abc12345:{}", "verdict": "allowed", "profile_id": "housecat",
    }
    denied = {
        "ts": "2026-07-10T00:00:00+00:00", "session": "s1", "tool": "Bash",
        "input_digest": "abc12345:{}", "verdict": "denied", "threat_class": "unauthorized-tool-use",
        "profile_id": "housecat",
    }
    _post(server, "/event", allowed)
    _post(server, "/event", denied)
    status, entries = _get(server, "/events")
    assert status == 200
    assert entries[0]["meow_lines"] == [entries[0]["meow"]]
    assert len(entries[1]["meow_lines"]) == 3
    assert " ".join(entries[1]["meow_lines"]) == entries[1]["meow"]


def test_hold_resolves_to_allow_when_decision_posted(running_listener):
    server, _profile = running_listener
    event = {
        "ts": "2026-07-10T00:00:00+00:00", "session": "s1", "tool": "Bash",
        "input_digest": "abc12345:{}", "verdict": "held", "profile_id": "housecat",
    }

    result = {}

    def _hold():
        status, body = _post(server, "/event/hold", event, timeout=10)
        result["status"] = status
        result["body"] = body

    thread = threading.Thread(target=_hold)
    thread.start()

    entry_id = None
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and entry_id is None:
        status, pending = _get(server, "/event/hold/pending")
        if pending:
            entry_id = pending[0]["id"]
        else:
            time.sleep(0.05)
    assert entry_id is not None

    status, _ = _post(server, f"/event/hold/{entry_id}/decision", {"decision": "allow"})
    assert status == 204

    thread.join(timeout=10)
    assert result["status"] == 200
    assert result["body"]["decision"] == "allow"
    assert result["body"]["id"] == entry_id

    status, entries = _get(server, "/events")
    resolved = [e for e in entries if e["id"] == entry_id][0]
    assert resolved["status"] == "allowed"


def test_hold_times_out_to_deny_when_nobody_answers(running_listener, monkeypatch):
    server, _profile = running_listener
    monkeypatch.setattr(listen, "HOLD_WAIT_SECONDS", 0.3)
    event = {
        "ts": "2026-07-10T00:00:00+00:00", "session": "s1", "tool": "Bash",
        "input_digest": "abc12345:{}", "verdict": "held", "profile_id": "housecat",
    }

    status, body = _post(server, "/event/hold", event, timeout=10)
    assert status == 200
    assert body["decision"] == "deny"

    status, entries = _get(server, "/events")
    resolved = [e for e in entries if e["id"] == body["id"]][0]
    assert resolved["status"] == "denied"


def test_decision_on_unknown_id_returns_404(running_listener):
    server, _profile = running_listener
    status, _ = _post(server, "/event/hold/999/decision", {"decision": "allow"})
    assert status == 404


def test_handle_event_appends_to_persisted_event_history(running_listener):
    server, profile = running_listener
    event = {
        "ts": "2026-07-10T00:00:00+00:00", "session": "s1", "tool": "Read",
        "input_digest": "abc12345:{}", "verdict": "allowed", "profile_id": "housecat",
    }
    status, _ = _post(server, "/event", event)
    assert status == 204

    history_path = Path(profile.path) / listen.EVENT_HISTORY_FILENAME
    assert history_path.exists()
    lines = [json.loads(line) for line in history_path.read_text().splitlines() if line.strip()]
    assert len(lines) == 1
    assert lines[0]["tool"] == "Read"


def test_handle_event_appends_denied_events_too_for_the_purr(running_listener):
    server, profile = running_listener
    for verdict in ("allowed", "denied", "held"):
        event = {
            "ts": "2026-07-10T00:00:00+00:00", "session": "s1", "tool": "Bash",
            "input_digest": "abc12345:{}", "verdict": verdict, "profile_id": "housecat",
        }
        status, _ = _post(server, "/event", event)
        assert status == 204

    history_path = Path(profile.path) / listen.EVENT_HISTORY_FILENAME
    lines = [json.loads(line) for line in history_path.read_text().splitlines() if line.strip()]
    assert [l["verdict"] for l in lines] == ["allowed", "denied", "held"]


def test_decision_with_invalid_value_returns_400(running_listener):
    server, _profile = running_listener
    # Register a real pending hold first so a bad decision value is the
    # only thing under test.
    event = {"tool": "Bash", "verdict": "held"}
    thread = threading.Thread(target=lambda: _post(server, "/event/hold", event, timeout=10))
    thread.start()
    entry_id = None
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and entry_id is None:
        _, pending = _get(server, "/event/hold/pending")
        if pending:
            entry_id = pending[0]["id"]
        else:
            time.sleep(0.05)
    assert entry_id is not None

    status, _ = _post(server, f"/event/hold/{entry_id}/decision", {"decision": "maybe"})
    assert status == 400

    # Clean up: resolve it for real so the background thread doesn't
    # linger past the test.
    _post(server, f"/event/hold/{entry_id}/decision", {"decision": "deny"})
    thread.join(timeout=10)
