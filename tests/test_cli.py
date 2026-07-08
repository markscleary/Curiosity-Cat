"""Tests for the curiosity-cat compile and prove commands."""

import json
import sys

import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))

from curiosity_cat import cli


def test_compile_output_validity(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cli.cmd_compile(level="housecat", target="claude-code")

    profile_dirs = list((tmp_path / "curiosity-cat" / "profiles").iterdir())
    assert len(profile_dirs) == 1
    profile_dir = profile_dirs[0]

    settings = json.loads((profile_dir / "settings.json").read_text())
    assert "Bash(curl:*)" in settings["permissions"]["deny"]
    assert "Read(**/.env)" in settings["permissions"]["deny"]
    assert settings["sandbox"] == {"enabled": True}

    scope_policy = json.loads((profile_dir / "scope-policy.json").read_text())
    assert scope_policy["adventure_level"] == "housecat"

    assert (profile_dir / "standing-orders.md").exists()
    assert (profile_dir / "PROFILE.md").exists()


def test_prove_holds_for_compiled_profile(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cli.cmd_compile(level="housecat", target="claude-code")
    profile_dir = next((tmp_path / "curiosity-cat" / "profiles").iterdir())

    cli.cmd_prove(profile=str(profile_dir), observed=False)

    proof_dirs = list((profile_dir / "proof").iterdir())
    assert len(proof_dirs) == 1
    clean_bill = json.loads((proof_dirs[0] / "clean-bill.json").read_text())

    assert clean_bill["self_consistency_trials"]
    assert all(t["held"] for t in clean_bill["self_consistency_trials"])
    assert all(t["method"] == "self-consistency" for t in clean_bill["self_consistency_trials"])
    assert all(t["verdict"] == cli.SELF_CONSISTENCY_HELD for t in clean_bill["self_consistency_trials"])
    assert clean_bill["observed_trials"] == []
    assert "no-observed" in clean_bill["observed_note"]
    assert clean_bill["guidance_only"]
    assert (proof_dirs[0] / "CLEAN-BILL.md").exists()


def test_prove_fails_when_a_wall_is_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cli.cmd_compile(level="housecat", target="claude-code")
    profile_dir = next((tmp_path / "curiosity-cat" / "profiles").iterdir())

    settings_path = profile_dir / "settings.json"
    settings = json.loads(settings_path.read_text())
    settings["permissions"]["deny"] = [
        p for p in settings["permissions"]["deny"] if p != "Read(**/.env)"
    ]
    settings_path.write_text(json.dumps(settings, indent=2))

    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_prove(profile=str(profile_dir), observed=False)
    assert exc_info.value.code == 1

    proof_dirs = list((profile_dir / "proof").iterdir())
    clean_bill = json.loads((proof_dirs[0] / "clean-bill.json").read_text())
    failed = [t for t in clean_bill["self_consistency_trials"] if t["held"] is False]
    assert any(t["trial"] == "credential_env" for t in failed)
    assert all(t["verdict"] == cli.SELF_CONSISTENCY_NOT_HELD for t in failed)


def test_prove_skips_observed_when_no_claude_binary(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cli.cmd_compile(level="housecat", target="claude-code")
    profile_dir = next((tmp_path / "curiosity-cat" / "profiles").iterdir())

    monkeypatch.setattr(cli.shutil, "which", lambda name: None)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("should never spawn a session with no claude binary on PATH")

    monkeypatch.setattr(cli, "_spawn_observed_session", fail_if_called)

    cli.cmd_prove(profile=str(profile_dir))

    proof_dirs = list((profile_dir / "proof").iterdir())
    clean_bill = json.loads((proof_dirs[0] / "clean-bill.json").read_text())
    assert clean_bill["observed_trials"] == []
    assert "no `claude` binary" in clean_bill["observed_note"]


def test_prove_skips_observed_when_no_safe_candidate(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cli.cmd_compile(level="tiger", target="claude-code")
    profile_dir = next((tmp_path / "curiosity-cat" / "profiles").iterdir())

    monkeypatch.setattr(cli.shutil, "which", lambda name: "/usr/bin/claude")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("tiger has no wall safe to test live — should never spawn a session")

    monkeypatch.setattr(cli, "_spawn_observed_session", fail_if_called)

    cli.cmd_prove(profile=str(profile_dir))

    proof_dirs = list((profile_dir / "proof").iterdir())
    clean_bill = json.loads((proof_dirs[0] / "clean-bill.json").read_text())
    assert clean_bill["observed_trials"] == []
    assert "no wall safe to test live" in clean_bill["observed_note"]


def test_prove_observed_trial_held_when_denial_recorded(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cli.cmd_compile(level="housecat", target="claude-code")
    profile_dir = next((tmp_path / "curiosity-cat" / "profiles").iterdir())

    monkeypatch.setattr(cli.shutil, "which", lambda name: "/usr/bin/claude")
    monkeypatch.setattr(cli, "_spawn_observed_session", lambda argv, cwd, timeout=120: json.dumps({
        "result": "The command was denied by permission settings.",
        "permission_denials": [{"tool_name": "Bash", "tool_input": {"command": "curl ..."}}],
    }))

    cli.cmd_prove(profile=str(profile_dir))

    proof_dirs = list((profile_dir / "proof").iterdir())
    clean_bill = json.loads((proof_dirs[0] / "clean-bill.json").read_text())
    [trial] = clean_bill["observed_trials"]
    assert trial["method"] == "observed-deny"
    assert trial["held"] is True
    assert trial["verdict"].startswith("observed-deny: held")


def test_prove_observed_trial_fails_when_action_not_blocked(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cli.cmd_compile(level="housecat", target="claude-code")
    profile_dir = next((tmp_path / "curiosity-cat" / "profiles").iterdir())

    monkeypatch.setattr(cli.shutil, "which", lambda name: "/usr/bin/claude")
    monkeypatch.setattr(cli, "_spawn_observed_session", lambda argv, cwd, timeout=120: json.dumps({
        "result": "Ran the command; it reached the network layer.",
        "permission_denials": [],
    }))

    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_prove(profile=str(profile_dir))
    assert exc_info.value.code == 1

    proof_dirs = list((profile_dir / "proof").iterdir())
    clean_bill = json.loads((proof_dirs[0] / "clean-bill.json").read_text())
    [trial] = clean_bill["observed_trials"]
    assert trial["held"] is False
    assert "FAILED" in trial["verdict"]


def test_parse_observed_session_holds_on_recorded_denial():
    held, detail = cli._parse_observed_session(json.dumps({"permission_denials": [{"tool_name": "Bash"}]}))
    assert held is True
    assert "1 permission denial" in detail


def test_parse_observed_session_fails_when_no_denial_recorded():
    held, detail = cli._parse_observed_session(json.dumps({"permission_denials": []}))
    assert held is False


def test_parse_observed_session_inconclusive_on_bad_output():
    held, detail = cli._parse_observed_session("not json")
    assert held is None
    assert "not valid JSON" in detail

    held, detail = cli._parse_observed_session("")
    assert held is None
    assert "no session output" in detail


def test_select_observed_candidate_prefers_bash_over_write():
    perms = {"deny": ["Bash(curl:*)", "Write"]}
    candidate = cli._select_observed_candidate(perms)
    assert candidate["trial"] == "observed_bash_deny"


def test_select_observed_candidate_falls_back_to_write():
    perms = {"deny": [], "allow": ["Write(./**)"]}
    candidate = cli._select_observed_candidate(perms)
    assert candidate["trial"] == "observed_write_outside_scope"


def test_select_observed_candidate_none_when_nothing_safe():
    perms = {"deny": ["Bash(sudo:*)", "Bash(rm -rf:*)"]}
    assert cli._select_observed_candidate(perms) is None
