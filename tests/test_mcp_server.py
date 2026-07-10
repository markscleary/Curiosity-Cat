"""Tests for curiosity_cat.mcp_server — the check/report MCP tools, against
a mocked Danger Map (never a real network call).
"""

import asyncio
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from curiosity_cat import __version__, core, mcp_server


def test_server_metadata_is_in_c_cat_voice():
    assert mcp_server.mcp.name == "curiosity-cat"
    assert "\U0001F431" in mcp_server.mcp.instructions
    assert "check" in mcp_server.mcp.instructions
    assert "report" in mcp_server.mcp.instructions


def test_registered_tools_are_exactly_check_and_report():
    tools = asyncio.run(mcp_server.mcp.list_tools())
    assert {t.name for t in tools} == {"check", "report"}


def test_check_no_match(monkeypatch):
    monkeypatch.setattr(core, "_fetch_danger_map_recent", lambda limit=50: [])
    result = mcp_server.check("totally-fine.example.com")
    assert result["matched"] is False
    assert result["threat_classes"] == []
    assert result["atlas_references"] == []
    assert "not found" in result["sentence"] or "no Danger Map match" in result["sentence"]


def test_check_match_reports_threat_class_and_atlas_reference(monkeypatch):
    monkeypatch.setattr(core, "_fetch_danger_map_recent", lambda limit=50: [
        {"source": "https://evil.example.com", "threat_class": "unsafe-url"},
        {"source": "https://evil.example.com/steal", "threat_class": "unsafe-url"},
    ])
    result = mcp_server.check("evil.example.com")
    assert result["matched"] is True
    assert len(result["matches"]) == 2
    assert result["threat_classes"] == ["unsafe-url"]
    assert result["atlas_references"] == [
        {"threat_class": "unsafe-url", "atlas_id": "AML.T0011.003", "nist_rmf": "MEASURE"},
    ]
    assert "evil.example.com" in result["sentence"]
    assert "unsafe-url" in result["sentence"]


def test_check_match_with_no_threat_class_field_still_reports_the_miss_honestly(monkeypatch):
    monkeypatch.setattr(core, "_fetch_danger_map_recent", lambda limit=50: [
        {"source": "https://evil.example.com"},
    ])
    result = mcp_server.check("evil.example.com")
    assert result["matched"] is True
    assert result["threat_classes"] == []
    assert result["atlas_references"] == []


def test_check_via_call_tool_round_trip(monkeypatch):
    monkeypatch.setattr(core, "_fetch_danger_map_recent", lambda limit=50: [])
    [content] = asyncio.run(mcp_server.mcp.call_tool("check", {"candidate": "example.com"}))
    payload = json.loads(content.text)
    assert payload["candidate"] == "example.com"
    assert payload["matched"] is False


def _report_kwargs(**overrides):
    kwargs = dict(
        threat_class="unsafe-url",
        severity="scratched",
        source="https://evil.example.com",
        what_happened="agent followed a malicious redirect",
        action_taken="refused and flagged",
        lesson="verify redirects",
        grade="observed",
        indicator="evil.example.com",
        platform="claude-code",
        platform_version="1.2.3",
    )
    kwargs.update(overrides)
    return kwargs


def test_report_submits_immediately_the_tool_call_itself_is_consent(monkeypatch):
    monkeypatch.setattr(core, "_post_danger_map_report", lambda event, api_key=None: {"ok": True})
    result = mcp_server.report(**_report_kwargs())
    assert result["submitted"] is True
    assert result["payload"]["threat_class"] == "unsafe-url"
    assert result["payload"]["profile_version"] == __version__


def test_report_defaults_timestamp_to_now_when_omitted(monkeypatch):
    monkeypatch.setattr(core, "_post_danger_map_report", lambda event, api_key=None: {"ok": True})
    result = mcp_server.report(**_report_kwargs())
    assert result["payload"]["timestamp"]


def test_report_carries_optional_fields_when_given(monkeypatch):
    monkeypatch.setattr(core, "_post_danger_map_report", lambda event, api_key=None: {"ok": True})
    result = mcp_server.report(**_report_kwargs(adventure_level="housecat", agent_type="coding"))
    assert result["payload"]["adventure_level"] == "housecat"
    assert result["payload"]["agent_type"] == "coding"


def test_report_omits_optional_fields_when_not_given(monkeypatch):
    monkeypatch.setattr(core, "_post_danger_map_report", lambda event, api_key=None: {"ok": True})
    result = mcp_server.report(**_report_kwargs())
    assert "adventure_level" not in result["payload"]
    assert "agent_type" not in result["payload"]


def test_report_never_carries_a_raw_payload_field(monkeypatch):
    monkeypatch.setattr(core, "_post_danger_map_report", lambda event, api_key=None: {"ok": True})
    result = mcp_server.report(**_report_kwargs())
    assert set(result["payload"]) <= set(core.REQUIRED_REPORT_FIELDS) | {
        "agent_type", "adventure_level", "submitted_by", "framework", "region",
    }


def test_report_via_call_tool_requires_all_required_fields():
    incomplete = _report_kwargs()
    del incomplete["source"]
    with pytest.raises(Exception, match="source"):
        asyncio.run(mcp_server.mcp.call_tool("report", incomplete))
