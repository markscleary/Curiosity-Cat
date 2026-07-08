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


def _make_report_event(**overrides):
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


def test_tray_missing_profile_flag_exits_one(capsys):
    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_tray(profile=None)
    assert exc_info.value.code == 1
    assert "Missing --profile" in capsys.readouterr().err


def test_tray_lists_pending_items_in_cat_voice(tmp_path, capsys):
    from curiosity_cat import core
    core.queue_close_call(_make_report_event(), tmp_path)
    capsys.readouterr()

    cli.cmd_tray(profile=str(tmp_path))

    out = capsys.readouterr().out
    assert "Mouse Tray" in out
    assert "evil.example.com" in out
    assert "unsafe-url" in out
    assert "tray --approve 1" in out


def test_tray_approve_only_submits_named_ids(tmp_path, monkeypatch, capsys):
    from curiosity_cat import core
    core.queue_close_call(_make_report_event(indicator="one.example.com"), tmp_path)
    core.queue_close_call(_make_report_event(indicator="two.example.com"), tmp_path)
    monkeypatch.setattr(core, "_post_danger_map_report", lambda event, api_key=None: {"ok": True})
    capsys.readouterr()

    cli.cmd_tray(profile=str(tmp_path), approve="1")

    out = capsys.readouterr().out
    assert "[1] submitted" in out
    statuses = {r["id"]: r["status"] for r in core.list_tray(tmp_path)}
    assert statuses == {1: "submitted", 2: "pending"}


def test_vet_missing_profile_flag_exits_one(capsys):
    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_vet(profile=None)
    assert exc_info.value.code == 1
    assert "Missing --profile" in capsys.readouterr().err


def test_vet_rejects_non_profile_directory(tmp_path, capsys):
    not_a_profile = tmp_path / "nope"
    not_a_profile.mkdir()

    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_vet(profile=str(not_a_profile))
    assert exc_info.value.code == 1
    assert "does not look like a compiled profile directory" in capsys.readouterr().err


def test_vet_prints_one_sentence_per_axis(tmp_path, monkeypatch, capsys):
    from curiosity_cat import core
    monkeypatch.chdir(tmp_path)
    cli.cmd_compile(level="housecat", target="claude-code")
    profile_dir = next((tmp_path / "curiosity-cat" / "profiles").iterdir())
    monkeypatch.setattr(core, "_detect_platform_version", lambda: None)
    monkeypatch.setattr(core, "_fetch_danger_map_stats",
                         lambda timeout=10: {"schema_version": core._local_danger_map_schema_version()})
    capsys.readouterr()

    cli.cmd_vet(profile=str(profile_dir))

    out = capsys.readouterr().out
    assert "matches the currently installed version" in out
    assert "unchanged since this profile was compiled" in out
    assert "no `claude` binary" in out


def test_stories_prints_latest_story(capsys):
    cli.cmd_stories()
    out = capsys.readouterr().out
    assert out.startswith("\n--- ")
