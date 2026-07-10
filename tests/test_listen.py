"""Tests for the reference Watcher listener (curiosity_cat.listen)."""

import json
import sys
import threading
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
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, profile
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _post(server, path, payload):
    host, port = server.server_address
    data = json.dumps(payload).encode("utf-8") if payload is not None else b"not json"
    request = urllib.request.Request(f"http://{host}:{port}{path}", data=data, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code


def test_listener_queues_denied_event_to_mouse_tray_over_real_http(running_listener):
    server, profile = running_listener
    event = {
        "ts": "2026-07-10T00:00:00+00:00", "session": "s1", "tool": "Bash",
        "input_digest": "abc12345:{}", "verdict": "denied", "threat_class": "unauthorized-tool-use",
        "profile_id": "housecat",
    }
    status = _post(server, "/event", event)
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
    status = _post(server, "/event", event)
    assert status == 204
    assert core.list_tray(profile.path) == []


def test_listener_rejects_unknown_path(running_listener):
    server, _profile = running_listener
    status = _post(server, "/not-event", {"tool": "Bash", "verdict": "allowed"})
    assert status == 404


def test_listener_rejects_malformed_json(running_listener):
    server, _profile = running_listener
    status = _post(server, "/event", None)
    assert status == 400
