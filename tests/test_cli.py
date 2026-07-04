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
    assert settings["sandbox"] is True

    scope_policy = json.loads((profile_dir / "scope-policy.json").read_text())
    assert scope_policy["adventure_level"] == "housecat"

    assert (profile_dir / "standing-orders.md").exists()
    assert (profile_dir / "PROFILE.md").exists()


def test_prove_holds_for_compiled_profile(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cli.cmd_compile(level="housecat", target="claude-code")
    profile_dir = next((tmp_path / "curiosity-cat" / "profiles").iterdir())

    cli.cmd_prove(profile=str(profile_dir))

    proof_dirs = list((profile_dir / "proof").iterdir())
    assert len(proof_dirs) == 1
    clean_bill = json.loads((proof_dirs[0] / "clean-bill.json").read_text())

    assert clean_bill["mechanical_trials"]
    assert all(t["verdict"] == "PASS" for t in clean_bill["mechanical_trials"])
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
        cli.cmd_prove(profile=str(profile_dir))
    assert exc_info.value.code == 1

    proof_dirs = list((profile_dir / "proof").iterdir())
    clean_bill = json.loads((proof_dirs[0] / "clean-bill.json").read_text())
    failed = [t for t in clean_bill["mechanical_trials"] if t["verdict"] == "FAIL"]
    assert any(t["trial"] == "credential_env" for t in failed)
