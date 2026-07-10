"""Tests for the weekly Purr digest (curiosity_cat.purr)."""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from curiosity_cat import core, purr

NOW = datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc)


def _compiled_profile(tmp_path):
    return core.compile_profile("housecat", "claude-code", cwd=tmp_path)


def _write_event_history(profile_dir, events):
    path = Path(profile_dir) / purr.EVENT_HISTORY_FILENAME
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n")


def _queue_tray_report(profile_dir, threat_class, indicator, ts):
    report = {
        "timestamp": ts, "threat_class": threat_class, "severity": "scratched",
        "source": "hook:Bash", "what_happened": "The Bash tool matched a deny rule.",
        "action_taken": "denied before it executed", "lesson": "automatic hook-derived close call",
        "grade": core.GRADE_SUSPECTED, "indicator": indicator, "platform": "claude-code",
        "platform_version": "unknown", "profile_version": core.__version__,
    }
    return core.queue_close_call(report, profile_dir)


def _write_tray_record_queued_at(profile_dir, queued_at, threat_class, indicator):
    """queue_close_call() always stamps queued_at with the real wall clock,
    which a fixed test `now` can't control — write the Mouse Tray file
    directly so this profile has one record queued at an arbitrary,
    fully-controlled time instead.
    """
    path = Path(profile_dir) / core.TRAY_QUEUE_FILENAME
    queue = json.loads(path.read_text()) if path.exists() else []
    queue.append({
        "id": max((r["id"] for r in queue), default=0) + 1,
        "queued_at": queued_at,
        "status": "pending",
        "event": {"threat_class": threat_class, "indicator": indicator},
    })
    path.write_text(json.dumps(queue))


def test_load_event_history_returns_empty_list_when_no_file(tmp_path):
    profile = _compiled_profile(tmp_path)
    assert purr.load_event_history(profile.path) == []


def test_load_event_history_skips_torn_lines(tmp_path):
    profile = _compiled_profile(tmp_path)
    path = Path(profile.path) / purr.EVENT_HISTORY_FILENAME
    path.write_text('{"tool": "Read", "ts": "2026-07-10T00:00:00+00:00"}\n{not json\n')
    events = purr.load_event_history(profile.path)
    assert len(events) == 1
    assert events[0]["tool"] == "Read"


def test_quiet_week_reports_honestly_with_no_data(tmp_path):
    profile = _compiled_profile(tmp_path)
    text = purr.generate_purr(profile.path, days=7, now=NOW)
    assert "stayed curled up" in text
    assert "Nothing landed in the Mouse Tray" in text
    assert "quietest kind of week" in text


def test_purr_summarises_roaming_from_event_history(tmp_path):
    profile = _compiled_profile(tmp_path)
    _write_event_history(profile.path, [
        {"ts": NOW.isoformat(), "tool": "Read", "verdict": "allowed"},
        {"ts": NOW.isoformat(), "tool": "Read", "verdict": "allowed"},
        {"ts": NOW.isoformat(), "tool": "Write", "verdict": "allowed"},
    ])

    text = purr.generate_purr(profile.path, days=7, now=NOW)
    assert "3 watched moves" in text
    assert "2 tools" in text
    assert "Read" in text


def test_purr_summarises_avoided_from_mouse_tray(tmp_path):
    profile = _compiled_profile(tmp_path)
    _queue_tray_report(profile.path, "unauthorized-tool-use", "bash-deny-pattern", NOW.isoformat())

    text = purr.generate_purr(profile.path, days=7, now=NOW)
    assert "1 close call" in text
    assert "unauthorized-tool-use" in text
    assert "bash-deny-pattern" in text
    # Nine Lives voice: the reason comes straight from the shared Meow formatter.
    assert "denied outright at this adventure level" in text


def test_purr_excludes_events_and_tray_items_outside_the_window(tmp_path):
    profile = _compiled_profile(tmp_path)
    stale = NOW - timedelta(days=30)
    _write_event_history(profile.path, [{"ts": stale.isoformat(), "tool": "Read", "verdict": "allowed"}])
    _write_tray_record_queued_at(profile.path, stale.isoformat(), "unauthorized-tool-use", "bash-deny-pattern")

    text = purr.generate_purr(profile.path, days=7, now=NOW)
    assert "stayed curled up" in text
    assert "Nothing landed in the Mouse Tray" in text


def test_build_purr_is_pure_and_deterministic():
    events = [{"ts": NOW.isoformat(), "tool": "Bash", "verdict": "denied", "threat_class": "unsafe-url"}]
    tray = []
    cutoff = NOW - timedelta(days=7)

    text_a = purr.build_purr(events, tray, cutoff)
    text_b = purr.build_purr(events, tray, cutoff)
    assert text_a == text_b
    assert "Bash tried something and the fence said no" in text_a
