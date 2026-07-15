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
    monkeypatch.setenv("CURIOSITY_CAT_HOME", str(tmp_path))
    response = serve.handle_request({
        "id": 2, "method": "compile", "params": {"level": "housecat", "target": "claude-code"},
    })
    assert response["id"] == 2
    assert response["result"]["level"] == "housecat"
    assert Path(response["result"]["settings_path"]).exists()


def test_compile_round_trip_survives_a_finder_style_launch(tmp_path, monkeypatch):
    """APP-FIX-1 regression: a Finder-launched sidecar inherits cwd "/"
    (read-only) with no --profiles-dir override — the exact conditions that
    used to raise Errno 30 out of a bare `Path.cwd()` default. compile must
    still succeed by falling back to the resolved platform-default home,
    never touching cwd.
    """
    monkeypatch.chdir("/")
    monkeypatch.delenv("CURIOSITY_CAT_HOME", raising=False)
    fake_default_home = tmp_path / "resolved-home"
    monkeypatch.setattr(core, "_platform_default_home", lambda: fake_default_home)

    response = serve.handle_request({
        "id": 200, "method": "compile", "params": {"level": "housecat", "target": "claude-code"},
    })

    assert "error" not in response, response.get("error")
    assert response["result"]["level"] == "housecat"
    settings_path = Path(response["result"]["settings_path"])
    assert settings_path.exists()
    assert settings_path.is_relative_to(fake_default_home)


def test_compile_round_trip_honors_explicit_profiles_dir_from_the_app(tmp_path, monkeypatch):
    """Mirrors how the Tauri app calls compile (sidecar-client.js): it
    resolves its own app-data profiles dir and passes it explicitly, so the
    engine's own cwd/home resolution never even runs.
    """
    monkeypatch.chdir("/")
    explicit = tmp_path / "app-data" / "profiles"

    response = serve.handle_request({
        "id": 201, "method": "compile",
        "params": {"level": "housecat", "target": "claude-code", "profiles_dir": str(explicit)},
    })

    assert "error" not in response, response.get("error")
    settings_path = Path(response["result"]["settings_path"])
    assert settings_path.is_relative_to(explicit)


def test_compile_round_trip_reports_invalid_level_as_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CURIOSITY_CAT_HOME", str(tmp_path))
    response = serve.handle_request({
        "id": 3, "method": "compile", "params": {"level": "feral", "target": "claude-code"},
    })
    assert response["id"] == 3
    assert "error" in response
    assert "result" not in response


def test_prove_round_trip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CURIOSITY_CAT_HOME", str(tmp_path))
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


def test_apply_and_unapply_round_trip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CURIOSITY_CAT_HOME", str(tmp_path))
    project = tmp_path / "myproject"
    project.mkdir()
    compiled = serve.handle_request({
        "id": 30, "method": "compile", "params": {"level": "housecat", "target": "claude-code"},
    })["result"]

    apply_response = serve.handle_request({
        "id": 31, "method": "apply", "params": {"profile_dir": compiled["path"], "target": str(project)},
    })
    assert "error" not in apply_response, apply_response.get("error")
    assert Path(apply_response["result"]["settings_path"]).exists()

    unapply_response = serve.handle_request({
        "id": 32, "method": "unapply", "params": {"target": str(project)},
    })
    assert "error" not in unapply_response, unapply_response.get("error")
    assert unapply_response["result"]["restored"] is True
    assert not (project / ".claude" / "settings.json").exists()


def test_apply_requires_target():
    response = serve.handle_request({"id": 33, "method": "apply", "params": {"profile_dir": "/tmp/whatever"}})
    assert "error" in response


def test_unapply_requires_target():
    response = serve.handle_request({"id": 34, "method": "unapply", "params": {}})
    assert "error" in response


def test_estate_round_trip_lists_discovered_targets(tmp_path, monkeypatch):
    monkeypatch.setenv("CURIOSITY_CAT_DISCOVER_ROOTS", str(tmp_path))
    project = tmp_path / "some-project"
    (project / ".claude").mkdir(parents=True)

    response = serve.handle_request({"id": 35, "method": "estate", "params": {}})
    assert "error" not in response, response.get("error")
    labels = [t["label"] for t in response["result"]["targets"]]
    assert str(project) in labels


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
        "grade": "observed",
        "indicator": "evil.example.com",
        "platform": "claude-code",
        "platform_version": "1.2.3",
        "profile_version": "0.1.1",
    }
    response = serve.handle_request({
        "id": 9, "method": "report_close_call", "params": {"event": event},
    })
    assert response["result"]["submitted"] is False
    assert "consent" in response["result"]["reason"]


def _report_event(**overrides):
    event = {
        "timestamp": "2026-01-01T00:00:00Z",
        "threat_class": "unsafe-url",
        "severity": "scratched",
        "source": "https://evil.example.com",
        "what_happened": "agent followed a malicious redirect",
        "action_taken": "refused and flagged",
        "lesson": "verify redirects",
        "grade": "observed",
        "indicator": "evil.example.com",
        "platform": "claude-code",
        "platform_version": "1.2.3",
        "profile_version": "0.1.1",
    }
    event.update(overrides)
    return event


def test_queue_and_list_tray_round_trip(tmp_path):
    response = serve.handle_request({
        "id": 11, "method": "queue_close_call",
        "params": {"event": _report_event(), "profile_dir": str(tmp_path)},
    })
    assert response["result"]["id"] == 1
    assert response["result"]["status"] == "pending"

    response = serve.handle_request({
        "id": 12, "method": "list_tray", "params": {"profile_dir": str(tmp_path)},
    })
    assert [r["id"] for r in response["result"]] == [1]


def test_submit_approved_round_trip_only_submits_named_ids(tmp_path, monkeypatch):
    serve.handle_request({
        "id": 13, "method": "queue_close_call",
        "params": {"event": _report_event(), "profile_dir": str(tmp_path)},
    })
    monkeypatch.setattr(core, "_post_danger_map_report", lambda event, api_key=None: {"ok": True})

    response = serve.handle_request({
        "id": 14, "method": "submit_approved",
        "params": {"profile_dir": str(tmp_path), "ids": [1]},
    })
    [result] = response["result"]
    assert result["submitted"] is True


def test_vet_round_trip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CURIOSITY_CAT_HOME", str(tmp_path))
    compiled = serve.handle_request({
        "id": 15, "method": "compile", "params": {"level": "housecat", "target": "claude-code"},
    })["result"]
    monkeypatch.setattr(core, "_detect_platform_version", lambda: None)
    monkeypatch.setattr(core, "_fetch_danger_map_stats",
                         lambda timeout=10: {"schema_version": core._local_danger_map_schema_version()})

    response = serve.handle_request({
        "id": 16, "method": "vet", "params": {"profile_dir": compiled["path"]},
    })
    assert response["id"] == 16
    assert "matches the currently installed version" in response["result"]["profile_axis"]
    assert response["result"]["recompiled"] is False


def test_unknown_method_is_an_error():
    response = serve.handle_request({"id": 10, "method": "nonexistent_method", "params": {}})
    assert response["id"] == 10
    assert "unknown method" in response["error"]


def test_render_share_card_round_trip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CURIOSITY_CAT_HOME", str(tmp_path))
    compiled = serve.handle_request({
        "id": 20, "method": "compile", "params": {"level": "housecat", "target": "claude-code"},
    })["result"]
    clean_bill = serve.handle_request({
        "id": 21, "method": "prove", "params": {"profile_dir": compiled["path"], "observed": False},
    })["result"]

    response = serve.handle_request({
        "id": 22, "method": "render_share_card",
        "params": {"clean_bill_path": clean_bill["clean_bill_path"]},
    })
    assert response["id"] == 22
    assert "error" not in response
    assert Path(response["result"]["path"]).exists()


def test_render_share_card_requires_clean_bill_path():
    response = serve.handle_request({"id": 23, "method": "render_share_card", "params": {}})
    assert response["id"] == 23
    assert "clean_bill_path is required" in response["error"]


def test_purr_round_trip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CURIOSITY_CAT_HOME", str(tmp_path))
    compiled = serve.handle_request({
        "id": 24, "method": "compile", "params": {"level": "housecat", "target": "claude-code"},
    })["result"]

    response = serve.handle_request({
        "id": 25, "method": "purr", "params": {"profile_dir": compiled["path"]},
    })
    assert response["id"] == 25
    assert "error" not in response
    assert "stayed curled up" in response["result"]["text"]


def test_purr_requires_profile_dir():
    response = serve.handle_request({"id": 26, "method": "purr", "params": {}})
    assert response["id"] == 26
    assert "profile_dir is required" in response["error"]


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
