"""curiosity_cat.discover — the estate: every protectable surface on this
machine curiosity-cat can find, and the honest, per-target protection state
of each one.

This module exists to serve docs/app/APP_SPEC.md's Assignment Model: a
compiled profile protects nothing until applied to a target, so before
"protection" can mean anything, the operator needs a plain list of what
there *is* to protect. Nothing in this module compiles, applies, or writes
anything — it only looks and reports what it finds.

Four kinds of target:
  - claude-code-project — a directory containing a `.claude/` subdirectory
  - claude-code-global   — the operator's `~/.claude/settings.json`
  - agent-process        — a workspace directory under an agent-fleet root
                            (e.g. ~/.openclaw/workspace/<agent-id>), cross-
                            referenced against the live process list
  - mcp-server           — an MCP server configured in a Claude config file

Per-target protection state comes from a profile registry
(`<curiosity-cat-home>/registry.json`) that `core.apply()` writes to and
`core.unapply()` clears entries from (Assignment Model (c)). A target
absent from the registry — because it was never applied, or was applied
and then unapplied — is still honestly reported UNGUARDED, never guessed,
never defaulted to "probably fine".
"""

import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

from .core import resolve_home

# --- protection state ------------------------------------------------

UNGUARDED = "unguarded"
GUARDED = "guarded"

# <curiosity-cat-home>/registry.json — written by core.apply(), cleared
# per-entry by core.unapply(). Duplicated as core.REGISTRY_FILENAME (this
# module imports resolve_home from core, so the reverse import would
# cycle) — keep both filenames equal. A missing file is still the normal
# case for a fresh install: every target reports UNGUARDED, honestly,
# rather than falling back to an assumed-safe default.
REGISTRY_FILENAME = "registry.json"


@dataclass
class ProtectionState:
    """A target's current protection state — what, from what, since when
    (Assignment Model (e)). `guarded` is False for every target until an
    `apply` command exists and has actually run against it.
    """

    status: str = UNGUARDED
    level: Optional[str] = None
    applied_at: Optional[str] = None
    proof_date: Optional[str] = None
    profile_dir: Optional[str] = None

    @property
    def guarded(self):
        return self.status == GUARDED


def _load_registry(home=None):
    """Read <home>/registry.json. Returns {} if it doesn't exist yet (the
    normal case — see module docstring) or fails to parse; never raises.
    """
    home = Path(home) if home is not None else resolve_home()
    path = home / REGISTRY_FILENAME
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}


def protection_state_for(target_id, registry):
    """The ProtectionState for `target_id` given an already-loaded
    registry dict (see _load_registry). A target absent from the registry
    is UNGUARDED — the only honest reading when nothing recorded an apply.
    """
    entry = registry.get(target_id)
    if not entry:
        return ProtectionState(status=UNGUARDED)
    return ProtectionState(
        status=GUARDED,
        level=entry.get("level"),
        applied_at=entry.get("applied_at"),
        proof_date=entry.get("proof_date"),
        profile_dir=entry.get("profile_dir"),
    )


def format_protection(state):
    """One plain sentence answering Assignment Model (e): what is
    protected, from what, since when.
    """
    if not state.guarded:
        return "UNGUARDED — no profile applied, protects nothing"
    since = f" since {state.applied_at}" if state.applied_at else " (apply date unknown)"
    proof = f", last proved {state.proof_date}" if state.proof_date else ", never proved"
    return f"GUARDED — {state.level or 'unknown-level'} profile applied{since}{proof}"


# --- targets -----------------------------------------------------------

@dataclass
class Target:
    kind: str
    id: str
    label: str
    path: Optional[str] = None
    detail: dict = field(default_factory=dict)
    protection: ProtectionState = field(default_factory=ProtectionState)


@dataclass
class Inventory:
    targets: list
    discovered_at: str

    @property
    def worst_state(self):
        """The worst protection state across every target (Assignment
        Model (f) — this is what a tray icon reads). UNGUARDED if any
        target is unguarded, or if there are no targets at all: an empty
        estate is not a protected one.
        """
        if not self.targets:
            return UNGUARDED
        return UNGUARDED if any(not t.protection.guarded for t in self.targets) else GUARDED


# --- (a) Claude Code project directories --------------------------------

DISCOVER_ROOTS_ENV = "CURIOSITY_CAT_DISCOVER_ROOTS"
DEFAULT_MAX_DEPTH = 6

# Directories never worth descending into while hunting for `.claude/`:
# either huge and irrelevant (node_modules, Library, site-packages), or
# already-identified as a `.claude/` dir with nothing further to find
# inside it.
_SKIP_DIR_NAMES = {
    ".git", ".claude", ".hg", ".svn",
    "node_modules", "__pycache__", ".venv", "venv", "site-packages",
    ".cache", ".npm", ".cargo", ".rustup", ".tox",
    "Library", "Applications", ".Trash",
    "dist", "build", "target", ".next", ".turbo", "vendor",
}


def _default_project_roots():
    override = os.environ.get(DISCOVER_ROOTS_ENV)
    if override:
        return [p for p in override.split(os.pathsep) if p]
    return [str(Path.home())]


def _walk_bounded(root, max_depth):
    """Yield every directory reachable from `root` within `max_depth`
    levels, skipping symlinks (no cycles) and _SKIP_DIR_NAMES. A plain
    stack-based walk rather than os.walk so pruned directories are never
    even listed.
    """
    stack = [(Path(root), 0)]
    while stack:
        current, depth = stack.pop()
        yield current
        if depth >= max_depth:
            continue
        try:
            children = list(current.iterdir())
        except (PermissionError, OSError):
            continue
        for entry in children:
            if entry.name in _SKIP_DIR_NAMES or entry.is_symlink():
                continue
            try:
                if entry.is_dir():
                    stack.append((entry, depth + 1))
            except OSError:
                continue


def discover_claude_code_projects(roots=None, max_depth=DEFAULT_MAX_DEPTH):
    """Directories containing a `.claude/` subdirectory, searched under
    `roots` (default: $CURIOSITY_CAT_DISCOVER_ROOTS if set, else the
    user's home directory) to `max_depth` levels. Returns a sorted list of
    absolute directory paths as strings.
    """
    roots = roots if roots is not None else _default_project_roots()
    found = set()
    for root in roots:
        root_path = Path(root).expanduser()
        if not root_path.is_dir():
            continue
        for candidate in _walk_bounded(root_path, max_depth):
            if (candidate / ".claude").is_dir():
                found.add(str(candidate))
    return sorted(found)


# --- (b) global ~/.claude settings --------------------------------------

def discover_global_claude_settings(home_dir=None):
    """The operator's user-level Claude Code settings — distinct from any
    project's own `.claude/settings.json`. Returns {"path": ..., "exists":
    ...}; existence is reported honestly rather than assumed.
    """
    home_dir = Path(home_dir) if home_dir is not None else Path.home()
    settings_path = home_dir / ".claude" / "settings.json"
    return {"path": str(settings_path), "exists": settings_path.exists()}


# --- (c) running agent processes ----------------------------------------

WORKSPACE_ROOT_ENV = "OPENCLAW_WORKSPACE_ROOT"


def _default_workspace_root():
    override = os.environ.get(WORKSPACE_ROOT_ENV)
    if override:
        return Path(override).expanduser()
    return Path.home() / ".openclaw" / "workspace"


def _read_process_command_lines():
    """Best-effort live process command lines (`ps -axo command`). Never
    raises: a missing `ps`, a permission error, or a timeout just means no
    agent is reported as currently running, not a discovery failure.
    """
    try:
        result = subprocess.run(["ps", "-axo", "command"], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    return result.stdout.splitlines()


def discover_agent_processes(workspace_root=None, process_lines=None):
    """Agent workspace directories under `workspace_root` (default
    ~/.openclaw/workspace, override via $OPENCLAW_WORKSPACE_ROOT), each
    cross-referenced against the live process list to say whether an agent
    process is actually running against that workspace right now.

    `process_lines` overrides the process list (for tests); defaults to a
    real `ps -axo command` read. A workspace directory existing on disk
    with no matching process is reported not-running, honestly, rather
    than omitted — it is still a target with a protection state, whether
    or not anything is using it at this exact moment.

    Returns a list of dicts: agent_id, workspace, running.
    """
    workspace_root = Path(workspace_root) if workspace_root is not None else _default_workspace_root()
    if not workspace_root.is_dir():
        return []

    lines = process_lines if process_lines is not None else _read_process_command_lines()

    agents = []
    for entry in sorted(workspace_root.iterdir()):
        if not entry.is_dir():
            continue
        workspace_str = str(entry)
        running = any(workspace_str in line for line in lines)
        agents.append({"agent_id": entry.name, "workspace": workspace_str, "running": running})
    return agents


# --- (d) configured MCP servers -----------------------------------------

def _read_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _mcp_entries_from_dict(servers_dict, scope, source):
    """Flatten one Claude config's `mcpServers` mapping into target dicts.

    Deliberately never carries `env`, `headers`, or `args` through — those
    routinely hold API keys and bearer tokens in a real Claude config.
    Only name, scope, source file, transport type, and command/url are
    reported, matching the Network Layer Principle a's "pattern not
    payload" discipline applied here to local discovery instead of a
    network report.
    """
    entries = []
    if not isinstance(servers_dict, dict):
        return entries
    for name, config in servers_dict.items():
        if not isinstance(config, dict):
            continue
        entries.append({
            "name": name,
            "scope": scope,
            "source": source,
            "type": config.get("type", "stdio"),
            "command": config.get("command") or config.get("url"),
        })
    return entries


def discover_mcp_servers(project_dirs=None, claude_json_path=None):
    """Configured MCP servers, read from Claude's own config files — never
    from curiosity-cat's own compiled profiles. Three sources, each
    labelled with its scope:
      - "user"                — the top-level "mcpServers" key of
                                 `claude_json_path` (default ~/.claude.json)
      - "project-local:<dir>" — that same file's
                                 "projects"[<dir>]["mcpServers"]
      - "project:<dir>"       — a `.mcp.json` at the root of each of
                                 `project_dirs`

    Returns a list of dicts: name, scope, source, type, command.
    """
    claude_json_path = Path(claude_json_path) if claude_json_path is not None else Path.home() / ".claude.json"
    servers = []

    claude_json = _read_json(claude_json_path) if claude_json_path.exists() else None
    if isinstance(claude_json, dict):
        servers += _mcp_entries_from_dict(claude_json.get("mcpServers"), "user", str(claude_json_path))
        projects = claude_json.get("projects")
        if isinstance(projects, dict):
            for project_path, project_config in projects.items():
                if isinstance(project_config, dict):
                    servers += _mcp_entries_from_dict(
                        project_config.get("mcpServers"), f"project-local:{project_path}", str(claude_json_path))

    for project_dir in (project_dirs or []):
        mcp_json_path = Path(project_dir) / ".mcp.json"
        if not mcp_json_path.exists():
            continue
        mcp_json = _read_json(mcp_json_path)
        if isinstance(mcp_json, dict):
            servers += _mcp_entries_from_dict(
                mcp_json.get("mcpServers"), f"project:{project_dir}", str(mcp_json_path))

    return servers


# --- the estate ----------------------------------------------------------

def build_inventory(roots=None, max_depth=DEFAULT_MAX_DEPTH, home_dir=None,
                     workspace_root=None, process_lines=None,
                     claude_json_path=None, registry_home=None):
    """The estate: every protectable surface this machine has, each with
    its current, honest, per-target protection state. Returns an
    Inventory. Nothing here writes anything — see docs/app/APP_SPEC.md's
    Assignment Model.
    """
    registry = _load_registry(registry_home)
    targets = []

    project_dirs = discover_claude_code_projects(roots=roots, max_depth=max_depth)
    for project_dir in project_dirs:
        target_id = f"claude-code-project:{project_dir}"
        targets.append(Target(
            kind="claude-code-project",
            id=target_id,
            label=project_dir,
            path=project_dir,
            protection=protection_state_for(target_id, registry),
        ))

    global_settings = discover_global_claude_settings(home_dir=home_dir)
    global_id = f"claude-code-global:{global_settings['path']}"
    targets.append(Target(
        kind="claude-code-global",
        id=global_id,
        label=global_settings["path"],
        path=global_settings["path"],
        detail={"exists": global_settings["exists"]},
        protection=protection_state_for(global_id, registry),
    ))

    for agent in discover_agent_processes(workspace_root=workspace_root, process_lines=process_lines):
        target_id = f"agent-process:{agent['workspace']}"
        targets.append(Target(
            kind="agent-process",
            id=target_id,
            label=agent["agent_id"],
            path=agent["workspace"],
            detail={"running": agent["running"]},
            protection=protection_state_for(target_id, registry),
        ))

    for server in discover_mcp_servers(project_dirs=project_dirs, claude_json_path=claude_json_path):
        target_id = f"mcp-server:{server['scope']}:{server['name']}"
        targets.append(Target(
            kind="mcp-server",
            id=target_id,
            label=server["name"],
            path=server["source"],
            detail={"scope": server["scope"], "type": server["type"], "command": server["command"]},
            protection=protection_state_for(target_id, registry),
        ))

    return Inventory(targets=targets, discovered_at=date.today().isoformat())
