"""Tests for the estate discovery engine (curiosity_cat.discover) —
docs/app/APP_SPEC.md's Assignment Model: a compiled profile protects
nothing until applied to a target, so discovery has to find every
protectable surface honestly, and report every one of them UNGUARDED
unless a profile registry says otherwise.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from curiosity_cat import discover


# --- (a) Claude Code project directories --------------------------------

def test_discover_claude_code_projects_finds_dirs_with_dot_claude(tmp_path):
    project = tmp_path / "my-project"
    (project / ".claude").mkdir(parents=True)
    other = tmp_path / "not-a-project"
    other.mkdir()

    found = discover.discover_claude_code_projects(roots=[str(tmp_path)])

    assert found == [str(project)]


def test_discover_claude_code_projects_finds_multiple_nested(tmp_path):
    a = tmp_path / "group" / "project-a"
    b = tmp_path / "group" / "project-b"
    (a / ".claude").mkdir(parents=True)
    (b / ".claude").mkdir(parents=True)

    found = discover.discover_claude_code_projects(roots=[str(tmp_path)])

    assert found == sorted([str(a), str(b)])


def test_discover_claude_code_projects_skips_heavy_dirs(tmp_path):
    (tmp_path / "node_modules" / "some-pkg" / ".claude").mkdir(parents=True)
    (tmp_path / ".git" / ".claude").mkdir(parents=True)
    real = tmp_path / "real-project"
    (real / ".claude").mkdir(parents=True)

    found = discover.discover_claude_code_projects(roots=[str(tmp_path)])

    assert found == [str(real)]


def test_discover_claude_code_projects_respects_max_depth(tmp_path):
    deep = tmp_path / "a" / "b" / "c" / "d" / "e" / "f" / "project"
    (deep / ".claude").mkdir(parents=True)

    found = discover.discover_claude_code_projects(roots=[str(tmp_path)], max_depth=2)

    assert found == []


def test_discover_claude_code_projects_ignores_missing_root(tmp_path):
    missing = tmp_path / "does-not-exist"
    found = discover.discover_claude_code_projects(roots=[str(missing)])
    assert found == []


def test_discover_claude_code_projects_env_override(tmp_path, monkeypatch):
    project = tmp_path / "env-project"
    (project / ".claude").mkdir(parents=True)
    monkeypatch.setenv(discover.DISCOVER_ROOTS_ENV, str(tmp_path))

    found = discover.discover_claude_code_projects()

    assert found == [str(project)]


# --- (b) global ~/.claude settings ---------------------------------------

def test_discover_global_claude_settings_reports_existing(tmp_path):
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text("{}")

    result = discover.discover_global_claude_settings(home_dir=tmp_path)

    assert result == {"path": str(settings), "exists": True}


def test_discover_global_claude_settings_reports_missing(tmp_path):
    result = discover.discover_global_claude_settings(home_dir=tmp_path)
    assert result["exists"] is False


# --- (c) running agent processes ----------------------------------------

def test_discover_agent_processes_marks_running_and_not_running(tmp_path):
    workspace_root = tmp_path / "workspace"
    quin = workspace_root / "quin"
    idle = workspace_root / "idle-agent"
    quin.mkdir(parents=True)
    idle.mkdir(parents=True)

    process_lines = [f"/usr/bin/claude --add-dir {quin}"]

    agents = discover.discover_agent_processes(workspace_root=workspace_root, process_lines=process_lines)

    by_id = {a["agent_id"]: a for a in agents}
    assert by_id["quin"]["running"] is True
    assert by_id["idle-agent"]["running"] is False


def test_discover_agent_processes_missing_workspace_root_returns_empty(tmp_path):
    missing = tmp_path / "no-such-dir"
    agents = discover.discover_agent_processes(workspace_root=missing, process_lines=[])
    assert agents == []


def test_discover_agent_processes_ignores_plain_files(tmp_path):
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    (workspace_root / "not-a-dir.txt").write_text("hi")
    (workspace_root / "real-agent").mkdir()

    agents = discover.discover_agent_processes(workspace_root=workspace_root, process_lines=[])

    assert [a["agent_id"] for a in agents] == ["real-agent"]


# --- (d) configured MCP servers ------------------------------------------

def test_discover_mcp_servers_reads_user_and_project_local_scope(tmp_path):
    claude_json = tmp_path / ".claude.json"
    claude_json.write_text(json.dumps({
        "mcpServers": {
            "gemini": {"type": "stdio", "command": "npx", "env": {"SECRET": "shh"}},
        },
        "projects": {
            "/some/project": {
                "mcpServers": {
                    "local-tool": {"type": "http", "url": "http://127.0.0.1:9/api"},
                },
            },
        },
    }))

    servers = discover.discover_mcp_servers(claude_json_path=claude_json)

    by_name = {s["name"]: s for s in servers}
    assert by_name["gemini"]["scope"] == "user"
    assert by_name["gemini"]["command"] == "npx"
    assert "env" not in by_name["gemini"]
    assert by_name["local-tool"]["scope"] == "project-local:/some/project"
    assert by_name["local-tool"]["command"] == "http://127.0.0.1:9/api"


def test_discover_mcp_servers_reads_project_dot_mcp_json(tmp_path):
    project = tmp_path / "a-project"
    project.mkdir()
    (project / ".mcp.json").write_text(json.dumps({
        "mcpServers": {
            "agent-mail": {"type": "http", "url": "http://127.0.0.1:8765/api/",
                            "headers": {"Authorization": "Bearer secret-token"}},
        },
    }))
    missing_claude_json = tmp_path / "no-such-claude.json"

    servers = discover.discover_mcp_servers(project_dirs=[str(project)], claude_json_path=missing_claude_json)

    assert len(servers) == 1
    assert servers[0]["name"] == "agent-mail"
    assert servers[0]["scope"] == f"project:{project}"
    assert "headers" not in servers[0]
    assert "Authorization" not in json.dumps(servers[0])


def test_discover_mcp_servers_no_configs_returns_empty(tmp_path):
    missing_claude_json = tmp_path / "no-such-claude.json"
    servers = discover.discover_mcp_servers(project_dirs=[], claude_json_path=missing_claude_json)
    assert servers == []


def test_discover_mcp_servers_tolerates_malformed_json(tmp_path):
    claude_json = tmp_path / ".claude.json"
    claude_json.write_text("{not valid json")
    servers = discover.discover_mcp_servers(claude_json_path=claude_json)
    assert servers == []


# --- protection state / registry -----------------------------------------

def test_protection_state_for_missing_entry_is_unguarded():
    state = discover.protection_state_for("some-target", {})
    assert state.guarded is False
    assert state.status == discover.UNGUARDED


def test_protection_state_for_present_entry_is_guarded():
    registry = {
        "some-target": {
            "level": "housecat",
            "applied_at": "2026-07-01",
            "proof_date": "2026-07-02",
            "profile_dir": "/somewhere/profile",
        },
    }
    state = discover.protection_state_for("some-target", registry)
    assert state.guarded is True
    assert state.level == "housecat"
    assert state.applied_at == "2026-07-01"
    assert state.proof_date == "2026-07-02"


def test_format_protection_unguarded_states_nothing_is_protected():
    text = discover.format_protection(discover.ProtectionState(status=discover.UNGUARDED))
    assert "UNGUARDED" in text
    assert "protects nothing" in text


def test_format_protection_guarded_states_what_from_since():
    state = discover.ProtectionState(status=discover.GUARDED, level="tiger",
                                      applied_at="2026-07-01", proof_date="2026-07-03")
    text = discover.format_protection(state)
    assert "GUARDED" in text
    assert "tiger" in text
    assert "2026-07-01" in text
    assert "2026-07-03" in text


def test_load_registry_missing_file_is_empty(tmp_path):
    assert discover._load_registry(home=tmp_path) == {}


def test_load_registry_reads_existing_file(tmp_path):
    (tmp_path / discover.REGISTRY_FILENAME).write_text(json.dumps({"t": {"level": "alleycat"}}))
    registry = discover._load_registry(home=tmp_path)
    assert registry == {"t": {"level": "alleycat"}}


def test_load_registry_tolerates_malformed_file(tmp_path):
    (tmp_path / discover.REGISTRY_FILENAME).write_text("{not valid")
    assert discover._load_registry(home=tmp_path) == {}


# --- the estate ------------------------------------------------------------

def test_build_inventory_assembles_all_target_kinds_unguarded(tmp_path):
    project = tmp_path / "roots" / "my-project"
    (project / ".claude").mkdir(parents=True)

    home_dir = tmp_path / "home"
    home_dir.mkdir()

    workspace_root = tmp_path / "workspace"
    (workspace_root / "quin").mkdir(parents=True)

    claude_json = tmp_path / ".claude.json"
    claude_json.write_text(json.dumps({"mcpServers": {"gemini": {"type": "stdio", "command": "npx"}}}))

    registry_home = tmp_path / "cc-home"
    registry_home.mkdir()

    inventory = discover.build_inventory(
        roots=[str(tmp_path / "roots")],
        home_dir=home_dir,
        workspace_root=workspace_root,
        process_lines=[],
        claude_json_path=claude_json,
        registry_home=registry_home,
    )

    kinds = {t.kind for t in inventory.targets}
    assert kinds == {"claude-code-project", "claude-code-global", "agent-process", "mcp-server"}
    assert all(not t.protection.guarded for t in inventory.targets)
    assert inventory.worst_state == discover.UNGUARDED


def test_build_inventory_worst_state_guarded_only_when_every_target_guarded(tmp_path):
    project = tmp_path / "roots" / "my-project"
    (project / ".claude").mkdir(parents=True)
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    claude_json = tmp_path / "no-claude.json"
    registry_home = tmp_path / "cc-home"
    registry_home.mkdir()

    target_id = f"claude-code-project:{project}"
    global_id = f"claude-code-global:{home_dir / '.claude' / 'settings.json'}"
    (registry_home / discover.REGISTRY_FILENAME).write_text(json.dumps({
        target_id: {"level": "housecat", "applied_at": "2026-07-01"},
        global_id: {"level": "housecat", "applied_at": "2026-07-01"},
    }))

    inventory = discover.build_inventory(
        roots=[str(tmp_path / "roots")],
        home_dir=home_dir,
        workspace_root=workspace_root,
        process_lines=[],
        claude_json_path=claude_json,
        registry_home=registry_home,
    )

    assert inventory.worst_state == discover.GUARDED
    assert all(t.protection.guarded for t in inventory.targets)


def test_build_inventory_empty_estate_is_unguarded():
    inventory = discover.Inventory(targets=[], discovered_at="2026-07-15")
    assert inventory.worst_state == discover.UNGUARDED
