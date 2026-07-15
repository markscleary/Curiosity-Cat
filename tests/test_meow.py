"""Tests for the shared Meow-voice formatter (curiosity_cat.meow)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from curiosity_cat import meow


def test_line_denied_says_hackles_up():
    text = meow.line({"tool": "Bash", "verdict": "denied"})
    assert "hackles up" in text
    assert "Bash" in text


def test_line_held_says_waiting():
    text = meow.line({"tool": "Write", "verdict": "held"})
    assert "waiting" in text
    assert "Write" in text


def test_line_allowed_says_no_trouble():
    text = meow.line({"tool": "Read", "verdict": "allowed"})
    assert "no trouble" in text
    assert "Read" in text


def test_line_falls_back_for_missing_tool():
    text = meow.line({"verdict": "allowed"})
    assert "something" in text


def test_block_sentences_is_exactly_three_sentences():
    sentences = meow.block_sentences({"tool": "Bash", "verdict": "denied", "threat_class": "credential-exposure"})
    assert len(sentences) == 3
    for sentence in sentences:
        assert sentence.strip().endswith(".")


def test_block_sentences_covers_what_why_and_what_to_do():
    sentences = meow.block_sentences({"tool": "Read", "verdict": "denied", "threat_class": "credential-exposure"})
    what_tried, why_no, what_to_do = sentences
    assert "Read" in what_tried
    assert "credential" in why_no
    assert "disagree" in what_to_do


def test_block_sentences_falls_back_honestly_for_unknown_threat_class():
    sentences = meow.block_sentences({"tool": "Bash", "verdict": "denied", "threat_class": "no-such-class"})
    assert "compiled profile's rules ruled it out" in sentences[1]


def test_block_sentences_falls_back_honestly_for_missing_threat_class():
    sentences = meow.block_sentences({"tool": "Bash", "verdict": "denied"})
    assert "compiled profile's rules ruled it out" in sentences[1]


def test_block_joins_all_three_sentences():
    text = meow.block({"tool": "Bash", "verdict": "denied", "threat_class": "unsafe-url"})
    assert text.count(". ") + 1 >= 3 or text.count(".") >= 3


def test_format_event_renders_denied_as_block():
    event = {"tool": "Bash", "verdict": "denied", "threat_class": "unsafe-url"}
    assert meow.format_event(event) == meow.block(event)


def test_format_event_renders_allowed_and_held_as_line():
    allowed = {"tool": "Read", "verdict": "allowed"}
    held = {"tool": "Bash", "verdict": "held"}
    assert meow.format_event(allowed) == meow.line(allowed)
    assert meow.format_event(held) == meow.line(held)


def test_format_event_lines_returns_three_for_denied():
    event = {"tool": "Bash", "verdict": "denied", "threat_class": "unsafe-url"}
    assert meow.format_event_lines(event) == meow.block_sentences(event)
    assert len(meow.format_event_lines(event)) == 3


def test_format_event_lines_returns_one_for_allowed_and_held():
    allowed = {"tool": "Read", "verdict": "allowed"}
    held = {"tool": "Bash", "verdict": "held"}
    assert meow.format_event_lines(allowed) == [meow.line(allowed)]
    assert meow.format_event_lines(held) == [meow.line(held)]


def test_never_leaks_input_digest_or_raw_payload():
    event = {
        "tool": "Bash", "verdict": "denied", "threat_class": "credential-exposure",
        "input_digest": "abc12345:{\"keys\": [\"file_path\"]}",
    }
    text = meow.format_event(event)
    assert "abc12345" not in text
