"""Tests for the PreToolUse approval gate (curiosity_cat.gate) — the
timeout-deny behaviour APP-4 asks for, exercised with a mocked HTTP round
trip rather than a real listener (see tests/test_listen.py for the real
socket version against curiosity_cat.listen's /event/hold endpoint).
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from curiosity_cat import gate


class _FakeResponse:
    def __init__(self, body):
        self._body = json.dumps(body).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def test_request_decision_returns_allow_only_on_explicit_allow(monkeypatch):
    monkeypatch.setattr(gate.urllib.request, "urlopen", lambda *a, **k: _FakeResponse({"decision": "allow"}))
    assert gate.request_decision({"tool": "Bash"}) == gate.DECISION_ALLOW


def test_request_decision_denies_on_explicit_deny(monkeypatch):
    monkeypatch.setattr(gate.urllib.request, "urlopen", lambda *a, **k: _FakeResponse({"decision": "deny"}))
    assert gate.request_decision({"tool": "Bash"}) == gate.DECISION_DENY


def test_request_decision_denies_on_malformed_response(monkeypatch):
    class _Garbage:
        def read(self):
            return b"not json"

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

    monkeypatch.setattr(gate.urllib.request, "urlopen", lambda *a, **k: _Garbage())
    assert gate.request_decision({"tool": "Bash"}) == gate.DECISION_DENY


def test_request_decision_denies_on_unexpected_decision_value(monkeypatch):
    monkeypatch.setattr(gate.urllib.request, "urlopen", lambda *a, **k: _FakeResponse({"decision": "sure, whatever"}))
    assert gate.request_decision({"tool": "Bash"}) == gate.DECISION_DENY


def test_request_decision_denies_when_listener_unreachable(monkeypatch):
    def _boom(*a, **k):
        raise OSError("connection refused")
    monkeypatch.setattr(gate.urllib.request, "urlopen", _boom)
    assert gate.request_decision({"tool": "Bash"}) == gate.DECISION_DENY


def test_request_decision_denies_on_timeout(monkeypatch):
    import socket

    def _timeout(*a, **k):
        raise socket.timeout("timed out")
    monkeypatch.setattr(gate.urllib.request, "urlopen", _timeout)
    assert gate.request_decision({"tool": "Bash"}, timeout=0.01) == gate.DECISION_DENY


@pytest.mark.parametrize("decision", [gate.DECISION_ALLOW, gate.DECISION_DENY])
def test_hook_output_shape_matches_claude_code_contract(decision):
    output = gate.hook_output(decision, {"tool": "Bash"})
    hook_specific = output["hookSpecificOutput"]
    assert hook_specific["hookEventName"] == "PreToolUse"
    assert hook_specific["permissionDecision"] == decision
    assert "Bash" in hook_specific["permissionDecisionReason"]


def test_hook_output_deny_reason_states_no_response_is_deny():
    output = gate.hook_output(gate.DECISION_DENY, {"tool": "Bash"})
    assert "no response = deny" in output["hookSpecificOutput"]["permissionDecisionReason"]
