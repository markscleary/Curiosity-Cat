"""Tests for the curiosity-cat engine (curiosity_cat.core)."""

import json
import sys
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
    monkeypatch.setattr(core, "_spawn_observed_session", lambda argv, cwd, timeout=120: json.dumps({
        "result": "The command was denied by permission settings.",
        "permission_denials": [{"tool_name": "Bash", "tool_input": {"command": "curl ..."}}],
    }))

    clean_bill = core.prove(profile.path)

    [trial] = clean_bill.observed_trials
    assert trial["method"] == "observed-deny"
    assert trial["held"] is True
    assert trial["verdict"].startswith("observed-deny: held")


def test_prove_observed_trial_fails_when_action_not_blocked(tmp_path, monkeypatch):
    profile = core.compile_profile("housecat", "claude-code", cwd=tmp_path)

    monkeypatch.setattr(core.shutil, "which", lambda name: "/usr/bin/claude")
    monkeypatch.setattr(core, "_spawn_observed_session", lambda argv, cwd, timeout=120: json.dumps({
        "result": "Ran the command; it reached the network layer.",
        "permission_denials": [],
    }))

    clean_bill = core.prove(profile.path)

    [trial] = clean_bill.observed_trials
    assert trial["held"] is False
    assert "FAILED" in trial["verdict"]
    assert clean_bill.passed is False


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


def test_report_close_call_withholds_submission_without_consent():
    event = {
        "timestamp": "2026-01-01T00:00:00Z",
        "threat_class": "unsafe-url",
        "severity": "scratched",
        "source": "https://evil.example.com",
        "what_happened": "agent followed a malicious redirect",
        "action_taken": "refused and flagged",
        "lesson": "verify redirects",
    }

    def fail_if_called(*args, **kwargs):
        raise AssertionError("must never submit without explicit consent")

    result = core.report_close_call(event, consent=False, submitter=fail_if_called)
    assert result["submitted"] is False
    assert "consent" in result["reason"]
    assert result["payload"] == event


def test_report_close_call_submits_with_consent():
    event = {
        "timestamp": "2026-01-01T00:00:00Z",
        "threat_class": "unsafe-url",
        "severity": "scratched",
        "source": "https://evil.example.com",
        "what_happened": "agent followed a malicious redirect",
        "action_taken": "refused and flagged",
        "lesson": "verify redirects",
    }
    submitter = lambda payload, api_key=None: {"ok": True}

    result = core.report_close_call(event, consent=True, submitter=submitter)
    assert result["submitted"] is True
    assert result["response"] == {"ok": True}


def test_report_close_call_handles_submission_failure():
    event = {
        "timestamp": "2026-01-01T00:00:00Z",
        "threat_class": "unsafe-url",
        "severity": "scratched",
        "source": "https://evil.example.com",
        "what_happened": "agent followed a malicious redirect",
        "action_taken": "refused and flagged",
        "lesson": "verify redirects",
    }

    def submitter(payload, api_key=None):
        raise OSError("connection refused")

    result = core.report_close_call(event, consent=True, submitter=submitter)
    assert result["submitted"] is False
    assert "failed" in result["reason"]
