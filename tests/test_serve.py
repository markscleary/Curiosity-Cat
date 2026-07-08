"""Round-trip tests for ccat-engine serve (curiosity_cat.serve)."""

import io
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from curiosity_cat import core, serve


def test_status_round_trip():
    response = serve.handle_request({"id": 1, "method": "status", "params": {}})
    assert response["id"] == 1
    assert response["result"]["engine"] == "ccat-engine"
    assert set(serve.METHODS) == set(response["result"]["methods"])
    assert "error" not in response


def test_compile_round_trip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    response = serve.handle_request({
        "id": 2, "method": "compile", "params": {"level": "housecat", "target": "claude-code"},
    })
    assert response["id"] == 2
    assert response["result"]["level"] == "housecat"
    assert Path(response["result"]["settings_path"]).exists()


def test_compile_round_trip_reports_invalid_level_as_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    response = serve.handle_request({
        "id": 3, "method": "compile", "params": {"level": "feral", "target": "claude-code"},
    })
    assert response["id"] == 3
    assert "error" in response
    assert "result" not in response


def test_prove_round_trip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    compiled = serve.handle_request({
        "id": 4, "method": "compile", "params": {"level": "housecat", "target": "claude-code"},
    })["result"]

    response = serve.handle_request({
        "id": 5, "method": "prove",
        "params": {"profile_dir": compiled["path"], "observed": False},
    })
    assert response["id"] == 5
    assert response["result"]["passed"] is True
    assert Path(response["result"]["clean_bill_path"]).exists()


def test_prove_round_trip_requires_profile_dir():
    response = serve.handle_request({"id": 6, "method": "prove", "params": {}})
    assert "error" in response


def test_check_round_trip(monkeypatch):
    monkeypatch.setattr(core, "_fetch_danger_map_recent",
                         lambda limit=50: [{"source": "https://evil.example.com"}])
    response = serve.handle_request({
        "id": 7, "method": "check", "params": {"candidate": "evil.example.com"},
    })
    assert response["id"] == 7
    assert response["result"]["matched"] is True


def test_check_round_trip_requires_candidate():
    response = serve.handle_request({"id": 8, "method": "check", "params": {}})
    assert "error" in response


def test_report_close_call_round_trip_withholds_without_consent():
    event = {
        "timestamp": "2026-01-01T00:00:00Z",
        "threat_class": "unsafe-url",
        "severity": "scratched",
        "source": "https://evil.example.com",
        "what_happened": "agent followed a malicious redirect",
        "action_taken": "refused and flagged",
        "lesson": "verify redirects",
    }
    response = serve.handle_request({
        "id": 9, "method": "report_close_call", "params": {"event": event},
    })
    assert response["result"]["submitted"] is False
    assert "consent" in response["result"]["reason"]


def test_unknown_method_is_an_error():
    response = serve.handle_request({"id": 10, "method": "purr", "params": {}})
    assert response["id"] == 10
    assert "unknown method" in response["error"]


def test_serve_forever_handles_bad_json_line_without_crashing():
    stdin = io.StringIO("not json at all\n")
    stdout = io.StringIO()
    serve.serve_forever(stdin=stdin, stdout=stdout)
    [line] = [l for l in stdout.getvalue().splitlines() if l.strip()]
    response = json.loads(line)
    assert response["id"] is None
    assert "invalid JSON" in response["error"]


def test_serve_forever_processes_multiple_lines():
    requests = [
        {"id": 1, "method": "status", "params": {}},
        {"id": 2, "method": "status", "params": {}},
    ]
    stdin = io.StringIO("\n".join(json.dumps(r) for r in requests) + "\n")
    stdout = io.StringIO()
    serve.serve_forever(stdin=stdin, stdout=stdout)
    lines = [json.loads(l) for l in stdout.getvalue().splitlines() if l.strip()]
    assert [r["id"] for r in lines] == [1, 2]
    assert all(r["result"]["engine"] == "ccat-engine" for r in lines)
