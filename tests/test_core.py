"""Tests for the curiosity-cat engine (curiosity_cat.core)."""

import json
import socket
import sys
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from curiosity_cat import core


def test_resolve_home_env_override_wins_over_everything(tmp_path, monkeypatch):
    override = tmp_path / "custom-home"
    monkeypatch.setenv("CURIOSITY_CAT_HOME", str(override))
    legacy = tmp_path / "curiosity-cat"
    legacy.mkdir()

    assert core.resolve_home(cwd=tmp_path) == override


def test_resolve_home_reuses_existing_legacy_dir_in_writable_cwd(tmp_path, monkeypatch):
    monkeypatch.delenv("CURIOSITY_CAT_HOME", raising=False)
    legacy = tmp_path / "curiosity-cat"
    legacy.mkdir()

    assert core.resolve_home(cwd=tmp_path) == legacy


def test_resolve_home_falls_back_to_platform_default_with_no_legacy_dir(tmp_path, monkeypatch):
    monkeypatch.delenv("CURIOSITY_CAT_HOME", raising=False)
    fake_default = tmp_path / "platform-default"
    monkeypatch.setattr(core, "_platform_default_home", lambda: fake_default)
    fresh_cwd = tmp_path / "fresh-project"
    fresh_cwd.mkdir()

    assert core.resolve_home(cwd=fresh_cwd) == fake_default


def test_resolve_home_falls_back_when_cwd_is_not_writable(tmp_path, monkeypatch):
    monkeypatch.delenv("CURIOSITY_CAT_HOME", raising=False)
    fake_default = tmp_path / "platform-default"
    monkeypatch.setattr(core, "_platform_default_home", lambda: fake_default)
    unwritable = tmp_path / "readonly-project"
    unwritable.mkdir()
    (unwritable / "curiosity-cat").mkdir()
    monkeypatch.setattr(core.os, "access", lambda path, mode: False)

    assert core.resolve_home(cwd=unwritable) == fake_default


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


# --- Assign: apply()/unapply() ---

def _apply_fixture(tmp_path, level="housecat"):
    profile = core.compile_profile(level, "claude-code", cwd=tmp_path)
    project = tmp_path / "target-project"
    project.mkdir()
    registry_home = tmp_path / "cc-home"
    return profile, project, registry_home


def test_apply_installs_compiled_settings_when_target_has_none(tmp_path):
    profile, project, registry_home = _apply_fixture(tmp_path)

    result = core.apply(profile.path, str(project), registry_home=registry_home)

    installed_path = project / ".claude" / "settings.json"
    assert installed_path.exists()
    assert json.loads(installed_path.read_text()) == json.loads(Path(profile.settings_path).read_text())

    assert result.settings_path == str(installed_path)
    assert result.level == "housecat"
    assert result.profile_id == Path(profile.path).name
    assert result.backup_path is None
    assert result.merged is False
    assert "no existing settings.json" in result.merge_report[0]


def test_apply_to_global_target_uses_home_dir_override(tmp_path):
    profile = core.compile_profile("housecat", "claude-code", cwd=tmp_path)
    home_dir = tmp_path / "operator-home"
    registry_home = tmp_path / "cc-home"

    result = core.apply(profile.path, "global", home_dir=home_dir, registry_home=registry_home)

    expected_path = home_dir / ".claude" / "settings.json"
    assert result.settings_path == str(expected_path)
    assert expected_path.exists()
    assert result.target_kind == "claude-code-global"


def test_apply_rejects_non_profile_directory(tmp_path):
    not_a_profile = tmp_path / "not-a-profile"
    not_a_profile.mkdir()
    with pytest.raises(core.InvalidProfileError):
        core.apply(str(not_a_profile), str(tmp_path / "target"))


def test_apply_backs_up_existing_settings_before_writing(tmp_path):
    profile, project, registry_home = _apply_fixture(tmp_path)
    claude_dir = project / ".claude"
    claude_dir.mkdir()
    original = {"permissions": {"allow": ["Read(./custom/**)"]}}
    (claude_dir / "settings.json").write_text(json.dumps(original, indent=2))

    result = core.apply(profile.path, str(project), registry_home=registry_home)

    assert result.backup_path is not None
    backup_path = Path(result.backup_path)
    assert backup_path.exists()
    assert json.loads(backup_path.read_text()) == original
    # Backup lives under curiosity-cat's own home, never inside the target.
    assert registry_home in backup_path.parents
    assert claude_dir not in backup_path.parents


def test_apply_merge_never_drops_operators_existing_rules(tmp_path):
    profile, project, registry_home = _apply_fixture(tmp_path)
    claude_dir = project / ".claude"
    claude_dir.mkdir()
    existing = {
        "permissions": {
            "allow": ["Read(./custom/**)"],
            "deny": ["Bash(operators-own-danger:*)"],
            "defaultMode": "acceptEdits",
        },
        "env": {"MY_CUSTOM_VAR": "1"},
    }
    (claude_dir / "settings.json").write_text(json.dumps(existing, indent=2))

    result = core.apply(profile.path, str(project), registry_home=registry_home)

    merged = json.loads((claude_dir / "settings.json").read_text())
    assert result.merged is True
    # Operator's own rules survive...
    assert "Read(./custom/**)" in merged["permissions"]["allow"]
    assert "Bash(operators-own-danger:*)" in merged["permissions"]["deny"]
    # ...their explicit defaultMode is never silently overwritten...
    assert merged["permissions"]["defaultMode"] == "acceptEdits"
    # ...an unrelated top-level key passes through untouched...
    assert merged["env"] == {"MY_CUSTOM_VAR": "1"}
    # ...and the compiled profile's own walls were still added.
    assert "Read(**/.env)" in merged["permissions"]["deny"]
    assert "Bash(curl:*)" in merged["permissions"]["deny"]

    report_text = " ".join(result.merge_report)
    assert "preserved" in report_text
    assert "added" in report_text
    assert "env" in report_text


def test_apply_merge_reports_but_does_not_raise_on_malformed_existing_json(tmp_path):
    profile, project, registry_home = _apply_fixture(tmp_path)
    claude_dir = project / ".claude"
    claude_dir.mkdir()
    (claude_dir / "settings.json").write_text("{not valid json")

    result = core.apply(profile.path, str(project), registry_home=registry_home)

    assert result.backup_path is not None
    assert Path(result.backup_path).read_text() == "{not valid json"
    assert any("not valid JSON" in line for line in result.merge_report)
    # Recovers by installing the compiled profile as the merge base.
    merged = json.loads((claude_dir / "settings.json").read_text())
    assert "Read(**/.env)" in merged["permissions"]["deny"]


def test_apply_records_registry_entry_matching_discover_target_id(tmp_path):
    profile, project, registry_home = _apply_fixture(tmp_path, level="tiger")

    result = core.apply(profile.path, str(project), registry_home=registry_home)

    registry = json.loads((registry_home / core.REGISTRY_FILENAME).read_text())
    assert set(registry.keys()) == {result.target_id}
    entry = registry[result.target_id]
    assert entry["target"] == str(project)
    assert entry["profile_id"] == Path(profile.path).name
    assert entry["level"] == "tiger"
    assert entry["applied_at"] == result.applied_at
    assert entry["backup_path"] is None
    assert entry["proof_date"] is None

    # discover.py reads this same file back via protection_state_for().
    from curiosity_cat import discover
    state = discover.protection_state_for(result.target_id, registry)
    assert state.guarded is True
    assert state.level == "tiger"


def test_apply_twice_reapplies_and_updates_registry(tmp_path):
    profile, project, registry_home = _apply_fixture(tmp_path)

    first = core.apply(profile.path, str(project), registry_home=registry_home)
    second = core.apply(profile.path, str(project), registry_home=registry_home)

    assert second.backup_path is not None  # the first apply's output got backed up in turn
    registry = json.loads((registry_home / core.REGISTRY_FILENAME).read_text())
    assert len(registry) == 1
    assert registry[first.target_id]["applied_at"] == second.applied_at


def test_unapply_restores_pre_apply_backup_exactly(tmp_path):
    profile, project, registry_home = _apply_fixture(tmp_path)
    claude_dir = project / ".claude"
    claude_dir.mkdir()
    original = {"permissions": {"allow": ["Read(./custom/**)"], "defaultMode": "default"}}
    (claude_dir / "settings.json").write_text(json.dumps(original, indent=2))

    core.apply(profile.path, str(project), registry_home=registry_home)
    result = core.unapply(str(project), registry_home=registry_home)

    assert result.restored_from_backup is True
    restored = json.loads((claude_dir / "settings.json").read_text())
    assert restored == original


def test_unapply_removes_file_when_nothing_existed_before_apply(tmp_path):
    profile, project, registry_home = _apply_fixture(tmp_path)

    core.apply(profile.path, str(project), registry_home=registry_home)
    result = core.unapply(str(project), registry_home=registry_home)

    assert result.restored_from_backup is False
    assert not (project / ".claude" / "settings.json").exists()


def test_unapply_clears_registry_entry(tmp_path):
    profile, project, registry_home = _apply_fixture(tmp_path)

    applied = core.apply(profile.path, str(project), registry_home=registry_home)
    core.unapply(str(project), registry_home=registry_home)

    registry = json.loads((registry_home / core.REGISTRY_FILENAME).read_text())
    assert applied.target_id not in registry


def test_unapply_raises_when_target_was_never_applied(tmp_path):
    registry_home = tmp_path / "cc-home"
    with pytest.raises(core.TargetNotAppliedError):
        core.unapply(str(tmp_path / "never-applied"), registry_home=registry_home)


def test_unapply_raises_when_backup_file_is_missing(tmp_path):
    profile, project, registry_home = _apply_fixture(tmp_path)
    claude_dir = project / ".claude"
    claude_dir.mkdir()
    (claude_dir / "settings.json").write_text(json.dumps({"permissions": {"allow": ["Read(./x/**)"]}}))

    result = core.apply(profile.path, str(project), registry_home=registry_home)
    Path(result.backup_path).unlink()

    with pytest.raises(core.TargetNotAppliedError):
        core.unapply(str(project), registry_home=registry_home)


def test_apply_unapply_round_trip_is_idempotent_on_repeat(tmp_path):
    profile, project, registry_home = _apply_fixture(tmp_path)
    claude_dir = project / ".claude"
    claude_dir.mkdir()
    original = {"permissions": {"allow": ["Read(./custom/**)"]}}
    (claude_dir / "settings.json").write_text(json.dumps(original, indent=2))

    core.apply(profile.path, str(project), registry_home=registry_home)
    core.unapply(str(project), registry_home=registry_home)

    assert json.loads((claude_dir / "settings.json").read_text()) == original
    assert json.loads((registry_home / core.REGISTRY_FILENAME).read_text()) == {}


def test_prove_with_target_requires_prior_apply(tmp_path):
    profile, project, registry_home = _apply_fixture(tmp_path)

    with pytest.raises(core.TargetNotAppliedError):
        core.prove(profile.path, observed=False, target=str(project), registry_home=registry_home)


def test_prove_with_target_reads_the_targets_real_installed_settings(tmp_path):
    profile, project, registry_home = _apply_fixture(tmp_path)
    core.apply(profile.path, str(project), registry_home=registry_home)

    # Simulate merge-time drift: the installed file no longer matches the
    # profile directory's own copy verbatim (an operator's extra deny rule
    # survived the merge). prove(target=...) must test *that* file.
    installed_path = project / ".claude" / "settings.json"
    installed = json.loads(installed_path.read_text())
    installed["permissions"]["deny"].remove("Read(**/.env)")
    installed_path.write_text(json.dumps(installed, indent=2))

    clean_bill = core.prove(profile.path, observed=False, target=str(project), registry_home=registry_home)

    assert clean_bill.passed is False
    assert clean_bill.applied_target == str(project)
    failed = [t for t in clean_bill.self_consistency_trials if t["held"] is False]
    assert any(t["trial"] == "credential_env" for t in failed)


def test_prove_with_target_stamps_registry_proof_date(tmp_path):
    profile, project, registry_home = _apply_fixture(tmp_path)
    applied = core.apply(profile.path, str(project), registry_home=registry_home)

    clean_bill = core.prove(profile.path, observed=False, target=str(project), registry_home=registry_home)

    registry = json.loads((registry_home / core.REGISTRY_FILENAME).read_text())
    assert registry[applied.target_id]["proof_date"] == clean_bill.date


# --- Assign: apply()/unapply()/prove() against a Hermes target -------------
#
# Every test here uses a throwaway tmp_path as the Hermes profiles root —
# never the real ~/.hermes/profiles on this machine (docs/app/APP_SPEC.md's
# build brief is explicit that real apply happens later with Mark, one
# agent first).

def _hermes_fixture(tmp_path, level="housecat"):
    profile = core.compile_profile(level, "claude-code", cwd=tmp_path)
    hermes_root = tmp_path / "hermes-profiles"
    (hermes_root / "quin").mkdir(parents=True)
    registry_home = tmp_path / "cc-home"
    return profile, hermes_root, registry_home


def test_apply_to_hermes_target_installs_under_curiosity_cat_subdir(tmp_path):
    profile, hermes_root, registry_home = _hermes_fixture(tmp_path)

    result = core.apply(profile.path, "hermes:quin", registry_home=registry_home, hermes_profiles_root=hermes_root)

    installed_path = hermes_root / "quin" / core.HERMES_CURIOSITY_CAT_SUBDIR / "settings.json"
    assert installed_path.exists()
    assert json.loads(installed_path.read_text()) == json.loads(Path(profile.settings_path).read_text())
    assert result.settings_path == str(installed_path)
    assert result.target_kind == "hermes-agent"
    assert result.target == "hermes:quin"
    assert result.backup_path is None

    # Never touches anything else already sitting in the agent's profile dir.
    assert sorted(p.name for p in (hermes_root / "quin").iterdir()) == [core.HERMES_CURIOSITY_CAT_SUBDIR]


def test_apply_to_hermes_target_default_root_honours_home_patch(tmp_path, monkeypatch):
    """With no hermes_profiles_root override and no $HERMES_PROFILES_ROOT,
    apply() falls back to Path.home()/.hermes/profiles — proof that a test
    patching Path.home() (as every other test here does via
    hermes_profiles_root=) fully controls where a Hermes apply can write,
    so nothing in this suite can ever reach the real ~/.hermes/profiles.
    """
    profile = core.compile_profile("housecat", "claude-code", cwd=tmp_path)
    fake_home = tmp_path / "fake-home"
    (fake_home / ".hermes" / "profiles" / "quin").mkdir(parents=True)
    registry_home = tmp_path / "cc-home"
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))
    monkeypatch.delenv("HERMES_PROFILES_ROOT", raising=False)

    core.apply(profile.path, "hermes:quin", registry_home=registry_home)

    installed = fake_home / ".hermes" / "profiles" / "quin" / core.HERMES_CURIOSITY_CAT_SUBDIR / "settings.json"
    assert installed.exists()


def test_apply_to_hermes_target_backs_up_existing_curiosity_cat_profile(tmp_path):
    profile, hermes_root, registry_home = _hermes_fixture(tmp_path)
    subdir = hermes_root / "quin" / core.HERMES_CURIOSITY_CAT_SUBDIR
    subdir.mkdir(parents=True)
    original = {"permissions": {"allow": ["Read(./custom/**)"]}}
    (subdir / "settings.json").write_text(json.dumps(original, indent=2))

    result = core.apply(profile.path, "hermes:quin", registry_home=registry_home, hermes_profiles_root=hermes_root)

    assert result.backup_path is not None
    assert json.loads(Path(result.backup_path).read_text()) == original
    assert result.merged is True


def test_apply_to_hermes_target_records_registry_entry_matching_discover_target_id(tmp_path):
    profile, hermes_root, registry_home = _hermes_fixture(tmp_path, level="tiger")

    result = core.apply(profile.path, "hermes:quin", registry_home=registry_home, hermes_profiles_root=hermes_root)

    registry = json.loads((registry_home / core.REGISTRY_FILENAME).read_text())
    entry = registry[result.target_id]
    assert entry["level"] == "tiger"

    from curiosity_cat import discover
    inventory = discover.build_inventory(
        roots=[str(tmp_path / "no-such-root")],
        home_dir=tmp_path / "no-such-home",
        workspace_root=tmp_path / "no-such-openclaw",
        process_lines=[],
        claude_json_path=tmp_path / "no-such-claude.json",
        registry_home=registry_home,
        hermes_profiles_root=hermes_root,
    )
    hermes_targets = {t.id: t for t in inventory.targets if t.kind == "hermes-agent"}
    assert result.target_id in hermes_targets
    assert hermes_targets[result.target_id].protection.guarded is True
    assert hermes_targets[result.target_id].protection.level == "tiger"


def test_unapply_hermes_target_restores_backup_and_clears_registry(tmp_path):
    profile, hermes_root, registry_home = _hermes_fixture(tmp_path)
    subdir = hermes_root / "quin" / core.HERMES_CURIOSITY_CAT_SUBDIR
    subdir.mkdir(parents=True)
    original = {"permissions": {"allow": ["Read(./custom/**)"]}}
    (subdir / "settings.json").write_text(json.dumps(original, indent=2))

    applied = core.apply(profile.path, "hermes:quin", registry_home=registry_home, hermes_profiles_root=hermes_root)
    result = core.unapply("hermes:quin", registry_home=registry_home, hermes_profiles_root=hermes_root)

    assert result.restored_from_backup is True
    assert json.loads((subdir / "settings.json").read_text()) == original
    registry = json.loads((registry_home / core.REGISTRY_FILENAME).read_text())
    assert applied.target_id not in registry


def test_prove_with_hermes_target_requires_prior_apply(tmp_path):
    profile, hermes_root, registry_home = _hermes_fixture(tmp_path)

    with pytest.raises(core.TargetNotAppliedError):
        core.prove(profile.path, target="hermes:quin", registry_home=registry_home, hermes_profiles_root=hermes_root)


def test_prove_with_hermes_target_skips_observed_trial_honestly(tmp_path):
    profile, hermes_root, registry_home = _hermes_fixture(tmp_path)
    core.apply(profile.path, "hermes:quin", registry_home=registry_home, hermes_profiles_root=hermes_root)

    clean_bill = core.prove(profile.path, target="hermes:quin",
                             registry_home=registry_home, hermes_profiles_root=hermes_root)

    assert clean_bill.applied_target == "hermes:quin"
    assert clean_bill.observed_trials == []
    assert "Hermes agents run via the hermes gateway" in clean_bill.observed_note
    assert len(clean_bill.self_consistency_trials) > 0
    assert clean_bill.passed is True


def test_prove_with_hermes_target_forced_observed_still_skips(tmp_path):
    """Even --no-observed's opposite (observed=True) never spawns a live
    `claude -p` session against a Hermes target — there is nothing real
    for it to observe yet (see core.HERMES_CURIOSITY_CAT_SUBDIR)."""
    profile, hermes_root, registry_home = _hermes_fixture(tmp_path)
    core.apply(profile.path, "hermes:quin", registry_home=registry_home, hermes_profiles_root=hermes_root)

    clean_bill = core.prove(profile.path, observed=True, target="hermes:quin",
                             registry_home=registry_home, hermes_profiles_root=hermes_root)

    assert clean_bill.observed_trials == []
    assert clean_bill.observed_note is not None


def test_prove_with_hermes_target_reads_the_agents_real_installed_settings(tmp_path):
    profile, hermes_root, registry_home = _hermes_fixture(tmp_path)
    core.apply(profile.path, "hermes:quin", registry_home=registry_home, hermes_profiles_root=hermes_root)

    installed_path = hermes_root / "quin" / core.HERMES_CURIOSITY_CAT_SUBDIR / "settings.json"
    installed = json.loads(installed_path.read_text())
    installed["permissions"]["deny"].remove("Read(**/.env)")
    installed_path.write_text(json.dumps(installed, indent=2))

    clean_bill = core.prove(profile.path, target="hermes:quin",
                             registry_home=registry_home, hermes_profiles_root=hermes_root)

    assert clean_bill.passed is False
    failed = [t for t in clean_bill.self_consistency_trials if t["held"] is False]
    assert any(t["trial"] == "credential_env" for t in failed)


def test_prove_with_hermes_target_stamps_registry_proof_date(tmp_path):
    profile, hermes_root, registry_home = _hermes_fixture(tmp_path)
    applied = core.apply(profile.path, "hermes:quin", registry_home=registry_home, hermes_profiles_root=hermes_root)

    clean_bill = core.prove(profile.path, target="hermes:quin",
                             registry_home=registry_home, hermes_profiles_root=hermes_root)

    registry = json.loads((registry_home / core.REGISTRY_FILENAME).read_text())
    assert registry[applied.target_id]["proof_date"] == clean_bill.date


def test_apply_unapply_hermes_round_trip_never_touches_other_agents(tmp_path):
    profile, hermes_root, registry_home = _hermes_fixture(tmp_path)
    (hermes_root / "explorer").mkdir(parents=True)

    core.apply(profile.path, "hermes:quin", registry_home=registry_home, hermes_profiles_root=hermes_root)
    core.unapply("hermes:quin", registry_home=registry_home, hermes_profiles_root=hermes_root)

    assert list((hermes_root / "explorer").iterdir()) == []


# --- Fleet: apply_many()/unapply_many() ---

def _fleet_fixture(tmp_path):
    registry_home = tmp_path / "cc-home"
    profiles_dir = tmp_path / "profiles"
    project1 = tmp_path / "project1"
    project1.mkdir()
    project2 = tmp_path / "project2"
    project2.mkdir()
    return registry_home, profiles_dir, project1, project2


def test_apply_many_backs_up_each_targets_existing_settings(tmp_path):
    registry_home, profiles_dir, project1, project2 = _fleet_fixture(tmp_path)
    claude_dir1 = project1 / ".claude"
    claude_dir1.mkdir()
    original1 = {"permissions": {"allow": ["Read(./custom-one/**)"]}}
    (claude_dir1 / "settings.json").write_text(json.dumps(original1))
    claude_dir2 = project2 / ".claude"
    claude_dir2.mkdir()
    original2 = {"permissions": {"allow": ["Read(./custom-two/**)"]}}
    (claude_dir2 / "settings.json").write_text(json.dumps(original2))

    result = core.apply_many("housecat", [str(project1), str(project2)], observed=False,
                              registry_home=registry_home, profiles_dir=profiles_dir)

    assert len(result.outcomes) == 2
    assert result.agents_proven == 2
    assert result.agents_failed == 0
    assert all(o.ok for o in result.outcomes)

    originals = {str(project1): original1, str(project2): original2}
    for outcome in result.outcomes:
        backup_path = Path(outcome.apply_result.backup_path)
        assert backup_path.exists()
        assert json.loads(backup_path.read_text()) == originals[outcome.target]
        # Every backup lives under curiosity-cat's own home, never inside
        # the target it backs up — same invariant a single apply() gives.
        assert registry_home in backup_path.parents

    # The operator's own pre-existing rule survives the conservative merge
    # at each target — same guarantee a single apply() gives, per-target.
    assert "Read(./custom-one/**)" in json.loads((claude_dir1 / "settings.json").read_text())["permissions"]["allow"]
    assert "Read(./custom-two/**)" in json.loads((claude_dir2 / "settings.json").read_text())["permissions"]["allow"]

    assert Path(result.fleet_clean_bill_path).exists()
    assert Path(result.fleet_clean_bill_md_path).exists()
    fleet_dict = json.loads(Path(result.fleet_clean_bill_path).read_text())
    assert fleet_dict["agents_proven"] == 2
    assert fleet_dict["targets_requested"] == 2


def test_apply_many_one_target_failing_never_stops_the_rest(tmp_path):
    registry_home, profiles_dir, project1, _project2 = _fleet_fixture(tmp_path)
    not_a_directory = tmp_path / "not-a-directory.txt"
    not_a_directory.write_text("this is a file, not a project directory")

    result = core.apply_many("housecat", [str(project1), str(not_a_directory)], observed=False,
                              registry_home=registry_home, profiles_dir=profiles_dir)

    assert len(result.outcomes) == 2
    by_target = {o.target: o for o in result.outcomes}

    good = by_target[str(project1)]
    assert good.ok is True
    assert good.error is None
    assert (project1 / ".claude" / "settings.json").exists()

    bad = by_target[str(not_a_directory)]
    assert bad.ok is False
    assert bad.error
    assert bad.apply_result is None
    assert bad.clean_bill is None

    assert result.agents_proven == 1
    assert result.agents_failed == 1

    # The fleet-wide Clean Bill still reports both targets, the failure
    # included, rather than silently dropping the one that failed.
    fleet_dict = json.loads(Path(result.fleet_clean_bill_path).read_text())
    assert fleet_dict["targets_requested"] == 2
    assert fleet_dict["agents_proven"] == 1
    fleet_targets = {o["target"]: o for o in fleet_dict["outcomes"]}
    assert fleet_targets[str(not_a_directory)]["ok"] is False
    assert fleet_targets[str(project1)]["ok"] is True


def test_apply_many_rejects_unknown_level(tmp_path):
    registry_home, profiles_dir, project1, _project2 = _fleet_fixture(tmp_path)
    with pytest.raises(core.InvalidLevelError):
        core.apply_many("not-a-real-level", [str(project1)], observed=False,
                         registry_home=registry_home, profiles_dir=profiles_dir)


def test_unapply_many_restores_every_currently_guarded_target(tmp_path):
    registry_home, profiles_dir, project1, project2 = _fleet_fixture(tmp_path)
    apply_result = core.apply_many("housecat", [str(project1), str(project2)], observed=False,
                                    registry_home=registry_home, profiles_dir=profiles_dir)
    assert apply_result.agents_proven == 2

    result = core.unapply_many(registry_home=registry_home)

    assert result.restored == 2
    assert result.failed == 0
    assert not (project1 / ".claude" / "settings.json").exists()
    assert not (project2 / ".claude" / "settings.json").exists()
    assert json.loads((registry_home / core.REGISTRY_FILENAME).read_text()) == {}


def test_unapply_many_one_target_failing_never_stops_the_rest(tmp_path):
    registry_home, profiles_dir, project1, project2 = _fleet_fixture(tmp_path)
    # project1 needs a pre-apply backup to sabotage below — give it a real
    # pre-existing settings.json, so apply() actually records a backup_path.
    claude_dir1 = project1 / ".claude"
    claude_dir1.mkdir()
    (claude_dir1 / "settings.json").write_text(json.dumps({"permissions": {"allow": ["Read(./x/**)"]}}))

    core.apply_many("housecat", [str(project1), str(project2)], observed=False,
                     registry_home=registry_home, profiles_dir=profiles_dir)

    registry = json.loads((registry_home / core.REGISTRY_FILENAME).read_text())
    project1_entry = registry[f"claude-code-project:{project1}"]
    Path(project1_entry["backup_path"]).unlink()  # sabotage one target's undo

    result = core.unapply_many(registry_home=registry_home)

    assert result.restored == 1
    assert result.failed == 1
    by_target = {o.target: o for o in result.outcomes}
    assert by_target[str(project1)].ok is False
    assert by_target[str(project1)].error
    assert by_target[str(project2)].ok is True
    # The one that failed keeps its registry entry (unapply() never clears
    # it without a successful restore) — still reported GUARDED, honestly.
    registry_after = json.loads((registry_home / core.REGISTRY_FILENAME).read_text())
    assert f"claude-code-project:{project1}" in registry_after
    assert f"claude-code-project:{project2}" not in registry_after


def test_unapply_many_explicit_targets_bypasses_the_registry(tmp_path):
    registry_home, profiles_dir, project1, project2 = _fleet_fixture(tmp_path)
    core.apply_many("housecat", [str(project1), str(project2)], observed=False,
                     registry_home=registry_home, profiles_dir=profiles_dir)

    result = core.unapply_many(targets=[str(project1)], registry_home=registry_home)

    assert result.restored == 1
    assert not (project1 / ".claude" / "settings.json").exists()
    # project2 was never named — still guarded afterwards.
    registry_after = json.loads((registry_home / core.REGISTRY_FILENAME).read_text())
    assert f"claude-code-project:{project2}" in registry_after


def test_apply_many_and_unapply_many_reconstruct_global_target_correctly(tmp_path):
    registry_home, profiles_dir, project1, _project2 = _fleet_fixture(tmp_path)
    home_dir = tmp_path / "operator-home"

    core.apply_many("housecat", [core.GLOBAL_TARGET], observed=False,
                     registry_home=registry_home, profiles_dir=profiles_dir, home_dir=home_dir)
    assert (home_dir / ".claude" / "settings.json").exists()

    # unapply_many() with targets=None must reconstruct the literal
    # "global" target string from the registry's target_kind, not reuse
    # the stored target label (which is the settings path, not "global").
    result = core.unapply_many(registry_home=registry_home, home_dir=home_dir)

    assert result.restored == 1
    assert result.failed == 0
    assert not (home_dir / ".claude" / "settings.json").exists()
