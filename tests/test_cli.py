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
    monkeypatch.setenv("CURIOSITY_CAT_HOME", str(tmp_path))
    cli.cmd_compile(level="housecat", target="claude-code")

    out = capsys.readouterr().out
    assert "Compiled Housecat profile for claude-code." in out
    assert "settings.json" in out
    assert "PROFILE.md" in out


def test_compile_rejects_unknown_level(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CURIOSITY_CAT_HOME", str(tmp_path))
    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_compile(level="feral", target="claude-code")
    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert 'Missing or unknown --level: "feral"' in err
    assert "Valid levels: housecat, alleycat, tiger" in err


def test_compile_rejects_unknown_target(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CURIOSITY_CAT_HOME", str(tmp_path))
    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_compile(level="housecat", target="cursor")
    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert 'Missing or unknown --target: "cursor"' in err


def test_prove_reports_clean_bill_and_exits_zero(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CURIOSITY_CAT_HOME", str(tmp_path))
    cli.cmd_compile(level="housecat", target="claude-code")
    profile_dir = next((tmp_path / "profiles").iterdir())
    capsys.readouterr()

    cli.cmd_prove(profile=str(profile_dir), observed=False)

    out = capsys.readouterr().out
    assert "Wrote:" in out
    assert "clean-bill.json" in out
    assert "Clean bill of health." in out


def test_prove_exits_nonzero_and_lists_failed_walls(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CURIOSITY_CAT_HOME", str(tmp_path))
    cli.cmd_compile(level="housecat", target="claude-code")
    profile_dir = next((tmp_path / "profiles").iterdir())

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
    monkeypatch.setenv("CURIOSITY_CAT_HOME", str(tmp_path))
    not_a_profile = tmp_path / "nope"
    not_a_profile.mkdir()

    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_prove(profile=str(not_a_profile))
    assert exc_info.value.code == 1
    assert "does not look like a compiled profile directory" in capsys.readouterr().err


def test_apply_prints_three_question_summary_and_installs(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CURIOSITY_CAT_HOME", str(tmp_path))
    project = tmp_path / "myproject"
    project.mkdir()

    cli.cmd_apply(level="housecat", target=str(project), observed=False)

    out = capsys.readouterr().out
    assert f"Applied Housecat profile to {project}." in out
    assert "What is now protected:" in out
    assert "From what:" in out
    assert "Since when:" in out
    assert (project / ".claude" / "settings.json").exists()


def test_apply_reports_merge_when_target_has_existing_settings(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CURIOSITY_CAT_HOME", str(tmp_path))
    project = tmp_path / "myproject"
    claude_dir = project / ".claude"
    claude_dir.mkdir(parents=True)
    (claude_dir / "settings.json").write_text(json.dumps({"permissions": {"allow": ["Read(./x/**)"]}}))
    capsys.readouterr()

    cli.cmd_apply(level="housecat", target=str(project), observed=False)

    out = capsys.readouterr().out
    assert "Backed up prior settings to:" in out
    assert "What was merged:" in out
    assert "preserved" in out


def test_apply_rejects_unknown_level(capsys):
    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_apply(level="feral", target="/tmp/whatever")
    assert exc_info.value.code == 1
    assert 'Missing or unknown --level: "feral"' in capsys.readouterr().err


def test_apply_missing_target_exits_one(capsys):
    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_apply(level="housecat", target=None)
    assert exc_info.value.code == 1
    assert "Missing --target" in capsys.readouterr().err


def test_unapply_missing_target_exits_one(capsys):
    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_unapply(target=None)
    assert exc_info.value.code == 1
    assert "Missing --target" in capsys.readouterr().err


def test_unapply_reports_error_when_target_never_applied(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CURIOSITY_CAT_HOME", str(tmp_path))

    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_unapply(target=str(tmp_path / "never-applied"))
    assert exc_info.value.code == 1
    assert "no applied profile found" in capsys.readouterr().err


def test_apply_then_unapply_round_trip_via_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CURIOSITY_CAT_HOME", str(tmp_path))
    project = tmp_path / "myproject"
    claude_dir = project / ".claude"
    claude_dir.mkdir(parents=True)
    original = {"permissions": {"allow": ["Read(./custom/**)"]}}
    (claude_dir / "settings.json").write_text(json.dumps(original, indent=2))
    capsys.readouterr()

    cli.cmd_apply(level="housecat", target=str(project), observed=False)
    capsys.readouterr()

    cli.cmd_unapply(target=str(project))
    out = capsys.readouterr().out
    assert f"Unapplied {project}." in out
    assert json.loads((claude_dir / "settings.json").read_text()) == original


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


def test_listen_missing_profile_flag_exits_one(capsys):
    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_listen(profile=None)
    assert exc_info.value.code == 1
    assert "Missing --profile" in capsys.readouterr().err


def test_listen_delegates_to_listen_serve_forever(tmp_path, monkeypatch):
    from curiosity_cat import listen

    calls = []
    monkeypatch.setattr(listen, "serve_forever", lambda profile_dir: calls.append(profile_dir))

    cli.cmd_listen(profile=str(tmp_path))

    assert calls == [str(tmp_path)]


def test_main_dispatches_listen_command(tmp_path, monkeypatch):
    from curiosity_cat import listen

    calls = []
    monkeypatch.setattr(listen, "serve_forever", lambda profile_dir: calls.append(profile_dir))
    monkeypatch.setattr(sys, "argv", ["curiosity-cat", "listen", "--profile", str(tmp_path)])

    cli.main()

    assert calls == [str(tmp_path)]


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
    monkeypatch.setenv("CURIOSITY_CAT_HOME", str(tmp_path))
    cli.cmd_compile(level="housecat", target="claude-code")
    profile_dir = next((tmp_path / "profiles").iterdir())
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


def test_card_missing_path_exits_one(capsys):
    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_card(clean_bill_path=None)
    assert exc_info.value.code == 1
    assert "Missing <clean-bill.json>" in capsys.readouterr().err


def test_card_rejects_missing_file(tmp_path, capsys):
    missing = tmp_path / "clean-bill.json"
    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_card(clean_bill_path=str(missing))
    assert exc_info.value.code == 1
    assert "does not exist" in capsys.readouterr().err


def test_card_writes_png_from_a_real_clean_bill(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CURIOSITY_CAT_HOME", str(tmp_path))
    cli.cmd_compile(level="housecat", target="claude-code")
    profile_dir = next((tmp_path / "profiles").iterdir())
    cli.cmd_prove(profile=str(profile_dir), observed=False)
    clean_bill_path = next(profile_dir.glob("proof/*/clean-bill.json"))
    capsys.readouterr()

    cli.cmd_card(clean_bill_path=str(clean_bill_path))

    out = capsys.readouterr().out
    assert "Wrote share card:" in out
    assert (clean_bill_path.parent / "share-card.png").exists()


def test_purr_missing_profile_flag_exits_one(capsys):
    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_purr(profile=None)
    assert exc_info.value.code == 1
    assert "Missing --profile" in capsys.readouterr().err


def test_purr_prints_a_digest_for_a_quiet_profile(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CURIOSITY_CAT_HOME", str(tmp_path))
    cli.cmd_compile(level="housecat", target="claude-code")
    profile_dir = next((tmp_path / "profiles").iterdir())
    capsys.readouterr()

    cli.cmd_purr(profile=str(profile_dir))

    out = capsys.readouterr().out
    assert "stayed curled up" in out


def test_compile_states_plainly_it_is_not_yet_assigned(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CURIOSITY_CAT_HOME", str(tmp_path))
    cli.cmd_compile(level="housecat", target="claude-code")

    out = capsys.readouterr().out
    assert "not yet assigned to any target" in out
    assert "protects nothing until it is" in out


def test_estate_prints_empty_estate_honestly(monkeypatch, capsys, tmp_path):
    from curiosity_cat import discover
    monkeypatch.setattr(discover, "build_inventory",
                         lambda: discover.Inventory(targets=[], discovered_at="2026-07-15"))

    cli.cmd_estate()

    out = capsys.readouterr().out
    assert "0 target(s) found" in out
    assert "No protectable surfaces found" in out


def test_estate_prints_targets_grouped_with_worst_state(monkeypatch, capsys):
    from curiosity_cat import discover

    def _fake_inventory():
        return discover.Inventory(
            targets=[
                discover.Target(
                    kind="claude-code-project",
                    id="claude-code-project:/tmp/proj",
                    label="/tmp/proj",
                    path="/tmp/proj",
                    protection=discover.ProtectionState(status=discover.UNGUARDED),
                ),
                discover.Target(
                    kind="mcp-server",
                    id="mcp-server:user:gemini",
                    label="gemini",
                    protection=discover.ProtectionState(status=discover.UNGUARDED),
                    detail={"scope": "user"},
                ),
            ],
            discovered_at="2026-07-15",
        )

    monkeypatch.setattr(discover, "build_inventory", _fake_inventory)

    cli.cmd_estate()

    out = capsys.readouterr().out
    assert "2 target(s) found" in out
    assert "Claude Code projects:" in out
    assert "/tmp/proj" in out
    assert "MCP servers:" in out
    assert "gemini" in out
    assert "UNGUARDED" in out
    assert "Worst protection state across this estate: UNGUARDED" in out
