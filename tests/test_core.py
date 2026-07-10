"""Tests for the curiosity-cat engine (curiosity_cat.core)."""

import json
import socket
import sys
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from curiosity_cat import core


def test_compile_profile_output_validity(tmp_path):
    profile = core.compile_profile("housecat", "claude-code", cwd=tmp_path)

    assert profile.level == "housecat"
    assert profile.target == "claude-code"

    profile_dirs = list((tmp_path / "curiosity-cat" / "profiles").iterdir())
    assert len(profile_dirs) == 1
    profile_dir = profile_dirs[0]
    assert str(profile_dir) == profile.path

    settings = json.loads((profile_dir / "settings.json").read_text())
    assert "Bash(curl:*)" in settings["permissions"]["deny"]
    assert "Read(**/.env)" in settings["permissions"]["deny"]
    assert settings["sandbox"] == {"enabled": True}

    scope_policy = json.loads((profile_dir / "scope-policy.json").read_text())
    assert scope_policy["adventure_level"] == "housecat"

    assert (profile_dir / "standing-orders.md").exists()
    assert (profile_dir / "PROFILE.md").exists()

    manifest = json.loads((profile_dir / "manifest.json").read_text())
    assert manifest["level"] == "housecat"
    assert manifest["target"] == "claude-code"
    assert manifest["profile_version"] == core.__version__
    assert manifest["danger_map_schema_version"]
    assert manifest["compiled_at"]


def test_compile_profile_rejects_unknown_level(tmp_path):
    with pytest.raises(core.InvalidLevelError):
        core.compile_profile("feral", "claude-code", cwd=tmp_path)


def test_compile_profile_rejects_unknown_target(tmp_path):
    with pytest.raises(core.InvalidTargetError):
        core.compile_profile("housecat", "cursor", cwd=tmp_path)


def test_prove_holds_for_compiled_profile(tmp_path):
    profile = core.compile_profile("housecat", "claude-code", cwd=tmp_path)

    clean_bill = core.prove(profile.path, observed=False)

    assert clean_bill.passed is True
    proof_dirs = list((Path(profile.path) / "proof").iterdir())
    assert len(proof_dirs) == 1
    clean_bill_json = json.loads((proof_dirs[0] / "clean-bill.json").read_text())

    assert clean_bill_json["self_consistency_trials"]
    assert all(t["held"] for t in clean_bill_json["self_consistency_trials"])
    assert all(t["method"] == "self-consistency" for t in clean_bill_json["self_consistency_trials"])
    assert all(t["verdict"] == core.SELF_CONSISTENCY_HELD for t in clean_bill_json["self_consistency_trials"])
    assert clean_bill_json["observed_trials"] == []
    assert "no-observed" in clean_bill.observed_note
    assert clean_bill.guidance_only
    assert (proof_dirs[0] / "CLEAN-BILL.md").exists()


def test_prove_fails_when_a_wall_is_missing(tmp_path):
    profile = core.compile_profile("housecat", "claude-code", cwd=tmp_path)

    settings_path = Path(profile.settings_path)
    settings = json.loads(settings_path.read_text())
    settings["permissions"]["deny"] = [
        p for p in settings["permissions"]["deny"] if p != "Read(**/.env)"
    ]
    settings_path.write_text(json.dumps(settings, indent=2))

    clean_bill = core.prove(profile.path, observed=False)
    assert clean_bill.passed is False

    failed = [t for t in clean_bill.self_consistency_trials if t["held"] is False]
    assert any(t["trial"] == "credential_env" for t in failed)
    assert all(t["verdict"] == core.SELF_CONSISTENCY_NOT_HELD for t in failed)


def test_prove_rejects_non_profile_directory(tmp_path):
    empty_dir = tmp_path / "not-a-profile"
    empty_dir.mkdir()
    with pytest.raises(core.InvalidProfileError):
        core.prove(str(empty_dir))


def test_prove_skips_observed_when_no_claude_binary(tmp_path, monkeypatch):
    profile = core.compile_profile("housecat", "claude-code", cwd=tmp_path)

    monkeypatch.setattr(core.shutil, "which", lambda name: None)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("should never spawn a session with no claude binary on PATH")

    monkeypatch.setattr(core, "_spawn_observed_session", fail_if_called)

    clean_bill = core.prove(profile.path)

    assert clean_bill.observed_trials == []
    assert "no `claude` binary" in clean_bill.observed_note


def test_prove_skips_observed_when_no_safe_candidate(tmp_path, monkeypatch):
    profile = core.compile_profile("tiger", "claude-code", cwd=tmp_path)

    monkeypatch.setattr(core.shutil, "which", lambda name: "/usr/bin/claude")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("tiger has no wall safe to test live — should never spawn a session")

    monkeypatch.setattr(core, "_spawn_observed_session", fail_if_called)

    clean_bill = core.prove(profile.path)

    assert clean_bill.observed_trials == []
    assert "no wall safe to test live" in clean_bill.observed_note


def test_prove_observed_trial_held_when_denial_recorded(tmp_path, monkeypatch):
    profile = core.compile_profile("housecat", "claude-code", cwd=tmp_path)

    monkeypatch.setattr(core.shutil, "which", lambda name: "/usr/bin/claude")
    monkeypatch.setattr(core, "_detect_platform_version", lambda: "1.2.3 (Claude Code)")
    monkeypatch.setattr(core, "_spawn_observed_session", lambda argv, cwd, timeout=120: json.dumps({
        "result": "The command was denied by permission settings.",
        "permission_denials": [{"tool_name": "Bash", "tool_input": {"command": "curl ..."}}],
    }))
    # Hook round-trip is exercised separately (test_prove_hook_roundtrip_trial_*
    # below) — here it's skipped so this test stays focused on the
    # pre-existing observed-deny trial alone.
    monkeypatch.setattr(core, "_start_watcher_listener", lambda watcher_profile_dir, timeout=2.0: None)

    clean_bill = core.prove(profile.path)

    trial = next(t for t in clean_bill.observed_trials if t["trial"] == "observed_bash_deny")
    assert trial["method"] == "observed-deny"
    assert trial["held"] is True
    assert trial["verdict"].startswith("observed-deny: held")
    assert clean_bill.platform_version == "1.2.3 (Claude Code)"

    hook_trial = next(t for t in clean_bill.observed_trials if t["trial"] == "hook_roundtrip")
    assert hook_trial["held"] is None
    assert "skipped" in hook_trial["verdict"]

    history = json.loads((Path(profile.path) / "wall-history.json").read_text())
    assert history == [{
        "wall": trial["trial"], "platform_version": "1.2.3 (Claude Code)",
        "verdict": "held", "date": clean_bill.date,
    }]


def test_prove_observed_trial_fails_when_action_not_blocked(tmp_path, monkeypatch):
    profile = core.compile_profile("housecat", "claude-code", cwd=tmp_path)

    monkeypatch.setattr(core.shutil, "which", lambda name: "/usr/bin/claude")
    monkeypatch.setattr(core, "_detect_platform_version", lambda: "1.2.3 (Claude Code)")
    monkeypatch.setattr(core, "_spawn_observed_session", lambda argv, cwd, timeout=120: json.dumps({
        "result": "Ran the command; it reached the network layer.",
        "permission_denials": [],
    }))
    monkeypatch.setattr(core, "_start_watcher_listener", lambda watcher_profile_dir, timeout=2.0: None)

    clean_bill = core.prove(profile.path)

    trial = next(t for t in clean_bill.observed_trials if t["trial"] == "observed_bash_deny")
    assert trial["held"] is False
    assert "FAILED" in trial["verdict"]
    assert clean_bill.passed is False

    history = json.loads((Path(profile.path) / "wall-history.json").read_text())
    assert history[0]["verdict"] == "failed"


def _watcher_port_in_use():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind((core.WATCHER_HOST, core.WATCHER_PORT))
        except OSError:
            return True
    return False


def test_prove_hook_roundtrip_trial_reaches_real_listener(tmp_path, monkeypatch):
    """End-to-end proof of item 4 of the Watcher brief: spawn the real
    reference listener, run a hooked denied action, confirm the event
    arrived. No real `claude` binary is needed for this — the fake
    `_spawn_observed_session` below stands in for what a live Claude Code
    session's PreToolUse hook would actually do (POST the denied event),
    and everything downstream of that POST (the real listener process, the
    real HTTP handler, the real queue_close_call) runs for real.
    """
    if _watcher_port_in_use():
        pytest.skip(f"{core.WATCHER_HOST}:{core.WATCHER_PORT} already in use on this machine")

    profile = core.compile_profile("housecat", "claude-code", cwd=tmp_path)

    monkeypatch.setattr(core.shutil, "which", lambda name: "/usr/bin/claude")
    monkeypatch.setattr(core, "_detect_platform_version", lambda: "1.2.3 (Claude Code)")

    def fake_spawn_session(argv, cwd, timeout=120):
        event = {
            "ts": "2026-07-10T00:00:00+00:00", "session": "hook-roundtrip-test", "tool": "Bash",
            "input_digest": 'deadbeef:{"keys": ["command"], "verb": "curl"}',
            "verdict": "denied", "threat_class": "unsafe-url", "profile_id": "housecat",
        }
        request = urllib.request.Request(
            f"http://{core.WATCHER_HOST}:{core.WATCHER_PORT}/event",
            data=json.dumps(event).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            urllib.request.urlopen(request, timeout=2).close()
        except OSError:
            pass  # no listener up yet for this particular call — fine, see below
        return json.dumps({
            "result": "The command was denied by permission settings.",
            "permission_denials": [{"tool_name": "Bash", "tool_input": {"command": "curl ..."}}],
        })

    monkeypatch.setattr(core, "_spawn_observed_session", fake_spawn_session)

    clean_bill = core.prove(profile.path)

    hook_trial = next(t for t in clean_bill.observed_trials if t["trial"] == "hook_roundtrip")
    assert hook_trial["held"] is True
    assert hook_trial["verdict"].startswith("hook-roundtrip: held")

    main_trial = next(t for t in clean_bill.observed_trials if t["trial"] == "observed_bash_deny")
    assert main_trial["held"] is True


def test_parse_observed_session_holds_on_recorded_denial():
    held, detail = core._parse_observed_session(json.dumps({"permission_denials": [{"tool_name": "Bash"}]}))
    assert held is True
    assert "1 permission denial" in detail


def test_parse_observed_session_fails_when_no_denial_recorded():
    held, detail = core._parse_observed_session(json.dumps({"permission_denials": []}))
    assert held is False


def test_parse_observed_session_inconclusive_on_bad_output():
    held, detail = core._parse_observed_session("not json")
    assert held is None
    assert "not valid JSON" in detail

    held, detail = core._parse_observed_session("")
    assert held is None
    assert "no session output" in detail


def test_select_observed_candidate_prefers_bash_over_write():
    perms = {"deny": ["Bash(curl:*)", "Write"]}
    candidate = core._select_observed_candidate(perms)
    assert candidate["trial"] == "observed_bash_deny"


def test_select_observed_candidate_falls_back_to_write():
    perms = {"deny": [], "allow": ["Write(./**)"]}
    candidate = core._select_observed_candidate(perms)
    assert candidate["trial"] == "observed_write_outside_scope"


def test_select_observed_candidate_none_when_nothing_safe():
    perms = {"deny": ["Bash(sudo:*)", "Bash(rm -rf:*)"]}
    assert core._select_observed_candidate(perms) is None


def test_check_requires_a_candidate():
    with pytest.raises(ValueError):
        core.check("")


def test_check_matches_candidate_against_recent_incidents():
    fetcher = lambda limit=50: [
        {"source": "https://evil.example.com/payload", "threat_class": "unsafe-url"},
        {"source": "some other incident", "threat_class": "other"},
    ]
    verdict = core.check("evil.example.com", fetcher=fetcher)
    assert verdict.matched is True
    assert len(verdict.matches) == 1
    assert verdict.candidate == "evil.example.com"
    assert verdict.note is None


def test_check_no_match_is_honestly_not_a_safety_claim():
    fetcher = lambda limit=50: [{"source": "https://unrelated.example.com"}]
    verdict = core.check("evil.example.com", fetcher=fetcher)
    assert verdict.matched is False
    assert verdict.matches == []


def test_check_reports_lookup_failure_without_raising():
    def fetcher(limit=50):
        raise OSError("network unreachable")

    verdict = core.check("evil.example.com", fetcher=fetcher)
    assert verdict.matched is False
    assert "unavailable" in verdict.note


def test_report_close_call_requires_fields():
    with pytest.raises(ValueError):
        core.report_close_call({"timestamp": "2026-01-01T00:00:00Z"})


def make_report_event(**overrides):
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


def test_report_close_call_withholds_submission_without_consent():
    event = make_report_event()

    def fail_if_called(*args, **kwargs):
        raise AssertionError("must never submit without explicit consent")

    result = core.report_close_call(event, consent=False, submitter=fail_if_called)
    assert result["submitted"] is False
    assert "consent" in result["reason"]
    assert result["payload"] == event


def test_report_close_call_submits_with_consent():
    event = make_report_event()
    submitter = lambda payload, api_key=None: {"ok": True}

    result = core.report_close_call(event, consent=True, submitter=submitter)
    assert result["submitted"] is True
    assert result["response"] == {"ok": True}


def test_report_close_call_handles_submission_failure():
    event = make_report_event()

    def submitter(payload, api_key=None):
        raise OSError("connection refused")

    result = core.report_close_call(event, consent=True, submitter=submitter)
    assert result["submitted"] is False
    assert "failed" in result["reason"]


# --- Mouse Tray ---

def test_queue_close_call_requires_report_fields(tmp_path):
    with pytest.raises(ValueError):
        core.queue_close_call({"timestamp": "2026-01-01T00:00:00Z"}, tmp_path)


def test_queue_close_call_requires_a_valid_grade(tmp_path):
    event = make_report_event(grade="pretty-sure")
    with pytest.raises(ValueError):
        core.queue_close_call(event, tmp_path)


def test_queue_close_call_appends_and_assigns_incrementing_ids(tmp_path):
    first = core.queue_close_call(make_report_event(indicator="one.example.com"), tmp_path)
    second = core.queue_close_call(make_report_event(indicator="two.example.com"), tmp_path)

    assert first["id"] == 1
    assert second["id"] == 2
    assert first["status"] == "pending"

    queue = json.loads((tmp_path / core.TRAY_QUEUE_FILENAME).read_text())
    assert [r["id"] for r in queue] == [1, 2]
    assert queue[0]["event"]["indicator"] == "one.example.com"


def test_list_tray_filters_by_status(tmp_path):
    core.queue_close_call(make_report_event(), tmp_path)
    core.queue_close_call(make_report_event(), tmp_path)
    core.submit_approved(tmp_path, [1], submitter=lambda payload, api_key=None: {"ok": True})

    assert [r["id"] for r in core.list_tray(tmp_path, status="submitted")] == [1]
    assert [r["id"] for r in core.list_tray(tmp_path, status="pending")] == [2]
    assert len(core.list_tray(tmp_path)) == 2


def test_submit_approved_only_submits_named_ids(tmp_path):
    core.queue_close_call(make_report_event(indicator="one.example.com"), tmp_path)
    core.queue_close_call(make_report_event(indicator="two.example.com"), tmp_path)
    core.queue_close_call(make_report_event(indicator="three.example.com"), tmp_path)

    submitted_payloads = []

    def submitter(payload, api_key=None):
        submitted_payloads.append(payload)
        return {"ok": True}

    results = core.submit_approved(tmp_path, [2], submitter=submitter)

    assert len(submitted_payloads) == 1
    assert submitted_payloads[0]["indicator"] == "two.example.com"
    assert results == [{"id": 2, "submitted": True, "reason": "submitted to the Danger Map",
                         "endpoint": core.DANGER_MAP_REPORT_URL, "payload": submitted_payloads[0],
                         "response": {"ok": True}}]

    queue = core.list_tray(tmp_path)
    statuses = {r["id"]: r["status"] for r in queue}
    assert statuses == {1: "pending", 2: "submitted", 3: "pending"}


def test_submit_approved_never_calls_submitter_for_unapproved_ids(tmp_path):
    core.queue_close_call(make_report_event(), tmp_path)
    core.queue_close_call(make_report_event(), tmp_path)

    calls = []

    def submitter(payload, api_key=None):
        calls.append(payload)
        return {"ok": True}

    core.submit_approved(tmp_path, [1], submitter=submitter)

    assert len(calls) == 1
    assert [r["id"] for r in core.list_tray(tmp_path, status="pending")] == [2]


def test_submit_approved_reports_unknown_and_already_submitted_ids(tmp_path):
    core.queue_close_call(make_report_event(), tmp_path)
    core.submit_approved(tmp_path, [1], submitter=lambda payload, api_key=None: {"ok": True})

    results = core.submit_approved(tmp_path, [1, 99], submitter=lambda payload, api_key=None: {"ok": True})
    by_id = {r["id"]: r for r in results}
    assert by_id[1]["submitted"] is False
    assert "already submitted" in by_id[1]["reason"]
    assert by_id[99]["submitted"] is False
    assert "no such queued id" in by_id[99]["reason"]


# --- Vet ---

def test_vet_rejects_non_profile_directory(tmp_path):
    empty_dir = tmp_path / "not-a-profile"
    empty_dir.mkdir()
    with pytest.raises(core.InvalidProfileError):
        core.vet(str(empty_dir))


def test_vet_reports_up_to_date_axes_for_a_freshly_compiled_profile(tmp_path, monkeypatch):
    profile = core.compile_profile("housecat", "claude-code", cwd=tmp_path)
    monkeypatch.setattr(core, "_detect_platform_version", lambda: None)

    schema_version = core._local_danger_map_schema_version()
    report = core.vet(profile.path, fetcher=lambda: {"schema_version": schema_version})

    assert "matches the currently installed version" in report.profile_axis
    assert "unchanged since this profile was compiled" in report.danger_map_axis
    assert "no `claude` binary" in report.platform_axis
    assert report.drift_signals == []
    assert report.recompiled is False
    assert report.new_clean_bill is None


def test_vet_reports_profile_version_drift(tmp_path, monkeypatch):
    profile = core.compile_profile("housecat", "claude-code", cwd=tmp_path)
    manifest_path = Path(profile.manifest_path)
    manifest = json.loads(manifest_path.read_text())
    manifest["profile_version"] = "0.0.1-old"
    manifest_path.write_text(json.dumps(manifest))
    monkeypatch.setattr(core, "_detect_platform_version", lambda: None)

    report = core.vet(profile.path, fetcher=lambda: {"schema_version": manifest["danger_map_schema_version"]})

    assert "0.0.1-old" in report.profile_axis
    assert "recompile to pick up any policy changes" in report.profile_axis


def test_vet_reports_danger_map_schema_drift(tmp_path, monkeypatch):
    profile = core.compile_profile("housecat", "claude-code", cwd=tmp_path)
    monkeypatch.setattr(core, "_detect_platform_version", lambda: None)

    def stale_fetcher():
        raise OSError("network unreachable")

    monkeypatch.setattr(core, "_local_danger_map_schema_version", lambda: "999")
    report = core.vet(profile.path, fetcher=stale_fetcher)

    assert "Danger Map schema drifted" in report.danger_map_axis


def test_vet_reports_platform_version_drift_since_last_observed_proof(tmp_path, monkeypatch):
    profile = core.compile_profile("housecat", "claude-code", cwd=tmp_path)
    monkeypatch.setattr(core.shutil, "which", lambda name: "/usr/bin/claude")
    monkeypatch.setattr(core, "_detect_platform_version", lambda: "1.0.0")
    monkeypatch.setattr(core, "_spawn_observed_session", lambda argv, cwd, timeout=120: json.dumps({
        "result": "denied", "permission_denials": [{"tool_name": "Bash"}],
    }))
    core.prove(profile.path)

    monkeypatch.setattr(core, "_detect_platform_version", lambda: "2.0.0")
    schema_version = core._local_danger_map_schema_version()
    report = core.vet(profile.path, fetcher=lambda: {"schema_version": schema_version})

    assert "Platform drifted" in report.platform_axis
    assert "1.0.0" in report.platform_axis
    assert "2.0.0" in report.platform_axis


def test_vet_flags_wall_verdict_that_changed_across_platform_versions(tmp_path, monkeypatch):
    profile = core.compile_profile("housecat", "claude-code", cwd=tmp_path)
    history_path = Path(profile.path) / core.WALL_HISTORY_FILENAME
    history_path.write_text(json.dumps([
        {"wall": "observed_bash_deny", "platform_version": "1.0.0", "verdict": "held", "date": "2026-06-01"},
        {"wall": "observed_bash_deny", "platform_version": "2.0.0", "verdict": "failed", "date": "2026-07-01"},
    ]))
    monkeypatch.setattr(core, "_detect_platform_version", lambda: None)

    schema_version = core._local_danger_map_schema_version()
    report = core.vet(profile.path, fetcher=lambda: {"schema_version": schema_version})

    assert report.drift_signals == [{
        "wall": "observed_bash_deny",
        "verdicts": {"1.0.0": "held", "2.0.0": "failed"},
    }]


def test_vet_is_read_only_without_recompile(tmp_path, monkeypatch):
    profile = core.compile_profile("housecat", "claude-code", cwd=tmp_path)
    monkeypatch.setattr(core, "_detect_platform_version", lambda: None)
    before = sorted(p.name for p in Path(profile.path).parent.iterdir())

    schema_version = core._local_danger_map_schema_version()
    core.vet(profile.path, fetcher=lambda: {"schema_version": schema_version})

    after = sorted(p.name for p in Path(profile.path).parent.iterdir())
    assert before == after
    assert list(Path(profile.path).rglob("proof")) == []


def test_vet_recompile_writes_a_fresh_dated_profile_and_leaves_the_original_untouched(tmp_path, monkeypatch):
    profile = core.compile_profile("housecat", "claude-code", cwd=tmp_path)
    original_manifest = (Path(profile.path) / "manifest.json").read_text()
    monkeypatch.setattr(core, "_detect_platform_version", lambda: None)

    schema_version = core._local_danger_map_schema_version()
    report = core.vet(profile.path, recompile=True, observed=False,
                       fetcher=lambda: {"schema_version": schema_version})

    assert report.recompiled is True
    assert report.new_clean_bill is not None
    assert report.new_clean_bill.passed is True
    assert report.new_clean_bill.profile_dir != profile.path
    assert (Path(profile.path) / "manifest.json").read_text() == original_manifest
    assert list(Path(profile.path).rglob("proof")) == []
