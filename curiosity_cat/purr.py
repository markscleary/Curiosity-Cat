"""curiosity_cat.purr — the weekly Purr (APP_SPEC.md CHARACTER SYSTEMS:
"weekly Purr — local scheduled digest, template-based Nine Lives voice,
zero LLM dependency in v1").

One paragraph, built entirely from fixed templates plus counts and names
read straight out of two local, already-persisted sources for a profile:

- **Event history** (`curiosity_cat/listen.py`'s `event-history.jsonl`) —
  every Watcher event this profile's listener has ever received, appended
  to disk as it happens (unlike the listener's in-memory `_EventLog`, which
  resets whenever the listener process restarts). This is where the cat
  roamed.
- **The Mouse Tray** (`core.list_tray`) — denied events with a
  `threat_class`, queued for operator review. This is what it avoided.

Nothing here is summarised or invented by a model: every sentence is a
template filled in from a count, a tool name, or a `threat_class` this
profile actually saw.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import core, meow
from .listen import EVENT_HISTORY_FILENAME

DEFAULT_WINDOW_DAYS = 7


def _event_history_path(profile_dir):
    return Path(profile_dir) / EVENT_HISTORY_FILENAME


def load_event_history(profile_dir):
    """Every event this profile's Watcher listener has recorded, oldest
    first. Empty if the listener has never run against this profile — a
    quiet week is a valid, honestly-reportable state, not an error.
    """
    path = _event_history_path(profile_dir)
    if not path.exists():
        return []
    events = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # a torn last line from a killed process — skip, don't fail the whole digest
    return events


def _parse_ts(value):
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _since(ts_value, cutoff):
    ts = _parse_ts(ts_value)
    return ts is not None and ts >= cutoff


def _plural(n, word):
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def _roamed_sentence(recent_events):
    if not recent_events:
        return "This cat stayed curled up on the windowsill this week — no watched session ran."

    tool_counts = {}
    for event in recent_events:
        tool = event.get("tool") or "something"
        tool_counts[tool] = tool_counts.get(tool, 0) + 1
    top_tool, top_count = max(tool_counts.items(), key=lambda kv: kv[1])

    return (f"This week the cat roamed through {_plural(len(recent_events), 'watched move')} "
            f"across {_plural(len(tool_counts), 'tool')}, mostly by {top_tool} "
            f"({_plural(top_count, 'time')}).")


def _avoided_sentence(recent_tray):
    if not recent_tray:
        return "Nothing landed in the Mouse Tray — no fence turned anyone away this week."

    class_counts = {}
    for record in recent_tray:
        threat_class = (record.get("event") or {}).get("threat_class") or "other"
        class_counts[threat_class] = class_counts.get(threat_class, 0) + 1
    top_class, top_class_count = max(class_counts.items(), key=lambda kv: kv[1])

    return (f"It backed away from {_plural(len(recent_tray), 'close call')} the fence caught — "
            f"mostly {top_class} ({_plural(top_class_count, 'time')}).")


def _interesting_sentence(recent_tray, recent_events):
    if recent_tray:
        latest = max(recent_tray, key=lambda r: r.get("queued_at") or "")
        event = latest.get("event") or {}
        threat_class = event.get("threat_class")
        indicator = event.get("indicator") or "something odd"
        reason = meow.reason_for_threat_class(threat_class)
        return f"The one worth telling: it reached for {indicator} — {reason}."

    denied = [e for e in recent_events if e.get("verdict") == "denied"]
    if denied:
        tool = denied[0].get("tool") or "something"
        return f"The one worth telling: {tool} tried something and the fence said no, quietly, once."

    return "The quietest kind of week — every move went through clean."


def build_purr(events, tray, cutoff):
    """Build the Purr paragraph from already-loaded events/tray, both
    filtered to entries at or after `cutoff`. Pure and deterministic — no
    I/O, no clock reads — so it's the one function tests exercise directly;
    generate_purr() below just owns reading files and the window math.
    """
    recent_events = [e for e in events if _since(e.get("ts"), cutoff)]
    recent_tray = [r for r in tray if _since(r.get("queued_at"), cutoff)]

    return " ".join([
        _roamed_sentence(recent_events),
        _avoided_sentence(recent_tray),
        _interesting_sentence(recent_tray, recent_events),
    ])


def generate_purr(profile_dir, days=DEFAULT_WINDOW_DAYS, now=None):
    """The weekly Purr for `profile_dir`, covering the last `days` days up
    to `now` (defaults to the current UTC time).
    """
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    events = load_event_history(profile_dir)
    tray = core.list_tray(profile_dir)
    return build_purr(events, tray, cutoff)
