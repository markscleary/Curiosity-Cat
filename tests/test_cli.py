"""Tests for the curiosity-cat CLI (curiosity_cat.cli) — a thin wrapper over
curiosity_cat.core. These confirm the user-facing behaviour (stdout,
stderr, exit codes) rather than re-testing core's own logic; see
test_core.py for that.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from curiosity_cat import cli


def test_compile_prints_created_files_and_exits_cleanly(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    cli.cmd_compile(level="housecat", target="claude-code")

    out = capsys.readouterr().out
    assert "Compiled Housecat profile for claude-code." in out
    assert "settings.json" in out
    assert "PROFILE.md" in out


def test_compile_rejects_unknown_level(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_compile(level="feral", target="claude-code")
    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert 'Missing or unknown --level: "feral"' in err
    assert "Valid levels: housecat, alleycat, tiger" in err


def test_compile_rejects_unknown_target(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_compile(level="housecat", target="cursor")
    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert 'Missing or unknown --target: "cursor"' in err


def test_prove_reports_clean_bill_and_exits_zero(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    cli.cmd_compile(level="housecat", target="claude-code")
    profile_dir = next((tmp_path / "curiosity-cat" / "profiles").iterdir())
    capsys.readouterr()

    cli.cmd_prove(profile=str(profile_dir), observed=False)

    out = capsys.readouterr().out
    assert "Wrote:" in out
    assert "clean-bill.json" in out
    assert "Clean bill of health." in out


def test_prove_exits_nonzero_and_lists_failed_walls(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    cli.cmd_compile(level="housecat", target="claude-code")
    profile_dir = next((tmp_path / "curiosity-cat" / "profiles").iterdir())

    settings_path = profile_dir / "settings.json"
    settings = json.loads(settings_path.read_text())
    settings["permissions"]["deny"] = [
        p for p in settings["permissions"]["deny"] if p != "Read(**/.env)"
    ]
    settings_path.write_text(json.dumps(settings, indent=2))
    capsys.readouterr()

    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_prove(profile=str(profile_dir), observed=False)
    assert exc_info.value.code == 1

    err = capsys.readouterr().err
    assert "wall(s) did NOT hold" in err
    assert "credential_env" in err
    assert "No safe claim." in err


def test_prove_missing_profile_flag_exits_one(capsys):
    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_prove(profile=None)
    assert exc_info.value.code == 1
    assert "Missing --profile" in capsys.readouterr().err


def test_prove_rejects_non_profile_directory(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    not_a_profile = tmp_path / "nope"
    not_a_profile.mkdir()

    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_prove(profile=str(not_a_profile))
    assert exc_info.value.code == 1
    assert "does not look like a compiled profile directory" in capsys.readouterr().err


def test_check_prints_matches(monkeypatch, capsys):
    from curiosity_cat import core
    monkeypatch.setattr(core, "_fetch_danger_map_recent",
                         lambda limit=50: [{"source": "https://evil.example.com"}])

    cli.cmd_check(candidate="evil.example.com")

    out = capsys.readouterr().out
    assert "Whisker check — evil.example.com" in out
    assert "1 matching Danger Map incident(s) found" in out


def test_check_missing_candidate_exits_one(capsys):
    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_check(candidate=None)
    assert exc_info.value.code == 1
    assert "Missing candidate" in capsys.readouterr().err


def test_report_prints_danger_map_instructions(capsys):
    cli.cmd_report()
    out = capsys.readouterr().out
    assert "POST https://pcmqmvcxqsaypuabrkgj.supabase.co/functions/v1/danger-map/report" in out
    assert '"threat_class"' in out


def test_stories_prints_latest_story(capsys):
    cli.cmd_stories()
    out = capsys.readouterr().out
    assert out.startswith("\n--- ")
