#!/usr/bin/env python3
"""curiosity-cat CLI — AI agent safety framework."""

import argparse
import json
import os
import re
import shutil
import sys
from datetime import date
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

ROLE_FILES = {
    "research":   ["general-safety.md", "research-agent.md"],
    "coding":     ["general-safety.md", "coding-agent.md"],
    "enterprise": ["general-safety.md", "enterprise-analyst.md"],
    "all":        ["general-safety.md", "research-agent.md", "coding-agent.md", "enterprise-analyst.md"],
}

LEVELS = ["housecat", "alleycat", "tiger"]

# Denies that hold at every adventure level — the safety floor. Widening
# the slider widens exploration, not this.
CREDENTIAL_DENY_PATTERNS = [
    "Read(**/.env)",
    "Read(**/.env.*)",
    "Read(**/*credentials*)",
    "Read(**/*.pem)",
    "Read(**/id_rsa*)",
    "Read(~/.ssh/**)",
    "Read(~/.aws/**)",
]
DESTRUCTIVE_DENY_PATTERNS = [
    "Bash(sudo:*)",
    "Bash(rm -rf:*)",
]

# Level definitions are target-agnostic ("abstract"). Each target emitter
# below reads these knobs and renders them into that tool's own config
# format — adding a new target is a new emitter function, not a rewrite
# of this table.
LEVEL_POLICY = {
    "housecat": {
        "label": "Housecat",
        "summary": "Cautious. Stay close to home. Standing orders followed. Nothing leaves the yard.",
        "abstract": {
            "read_scope": "project",
            "write_scope": "project",
            "web_allowed_domains": ["docs.anthropic.com", "docs.python.org"],
            "web_wide_open": False,
            "bash_deny": ["Bash(curl:*)", "Bash(wget:*)"],
            "bash_ask": [],
            "sandbox": True,
            "autonomy": "cautious",
        },
        "scope_policy": {
            "url_fetch": {"allowed_domains": ["docs.anthropic.com", "docs.python.org"], "blocked_tlds": [".zip", ".mov", ".top", ".xyz"], "max_redirect_hops": 1, "require_https": True},
            "downloads": {"allowed_types": ["txt", "md", "json", "csv"], "max_size_mb": 10, "quarantine_all": True},
            "credentials": {"never_transmit": True, "flag_requests": True},
            "packages": {"min_weekly_downloads": 5000, "min_age_days": 90, "block_postinstall": True},
            "data": {"strip_pii": True, "approved_endpoints": [], "flag_unknown_endpoints": True},
        },
    },
    "alleycat": {
        "label": "Alley Cat",
        "summary": "Balanced. Calculated risks accepted. Braver exploration. Still comes home.",
        "abstract": {
            "read_scope": "broad",
            "write_scope": "project",
            "web_allowed_domains": ["docs.anthropic.com", "docs.python.org", "github.com", "pypi.org", "npmjs.com", "stackoverflow.com"],
            "web_wide_open": False,
            "bash_deny": [],
            "bash_ask": ["Bash(curl:*)", "Bash(wget:*)", "Bash(npm install:*)", "Bash(pip install:*)", "Bash(pip3 install:*)", "Bash(brew install:*)", "Bash(yarn add:*)"],
            "sandbox": True,
            "autonomy": "balanced",
        },
        "scope_policy": {
            "url_fetch": {"allowed_domains": ["docs.anthropic.com", "docs.python.org", "github.com", "pypi.org", "npmjs.com", "stackoverflow.com"], "blocked_tlds": [".zip", ".mov", ".top", ".xyz"], "max_redirect_hops": 3, "require_https": True},
            "downloads": {"allowed_types": ["pdf", "docx", "txt", "csv", "json", "md", "html"], "max_size_mb": 50, "quarantine_all": True},
            "credentials": {"never_transmit": True, "flag_requests": True},
            "packages": {"min_weekly_downloads": 1000, "min_age_days": 30, "block_postinstall": True},
            "data": {"strip_pii": True, "approved_endpoints": [], "flag_unknown_endpoints": True},
        },
    },
    "tiger": {
        "label": "Tiger",
        "summary": "Daring. Widest range. Explores the edge. Reports back rare places and tales of danger.",
        "abstract": {
            "read_scope": "any",
            "write_scope": "any",
            "web_allowed_domains": [],
            "web_wide_open": True,
            "bash_deny": [],
            "bash_ask": [],
            "sandbox": True,
            "autonomy": "wide",
        },
        "scope_policy": {
            "url_fetch": {"allowed_domains": [], "blocked_tlds": [".zip", ".mov", ".top", ".xyz"], "max_redirect_hops": 5, "require_https": True},
            "downloads": {"allowed_types": ["pdf", "docx", "txt", "csv", "json", "md", "html"], "max_size_mb": 200, "quarantine_all": False},
            "credentials": {"never_transmit": True, "flag_requests": True},
            "packages": {"min_weekly_downloads": 100, "min_age_days": 7, "block_postinstall": True},
            "data": {"strip_pii": True, "approved_endpoints": [], "flag_unknown_endpoints": False},
        },
    },
}

AUTONOMY_TO_CLAUDE_CODE_MODE = {
    "cautious": "default",
    "balanced": "acceptEdits",
    "wide": "bypassPermissions",
}


def emit_claude_code_settings(level):
    """Render the abstract level policy into a real Claude Code settings.json."""
    a = LEVEL_POLICY[level]["abstract"]

    allow = []
    allow.append("Read(./**)" if a["read_scope"] == "project" else "Read(**)")
    allow.append("Write(./**)" if a["write_scope"] == "project" else "Write(**)")
    allow.append("Edit(./**)" if a["write_scope"] == "project" else "Edit(**)")

    deny = list(CREDENTIAL_DENY_PATTERNS) + list(DESTRUCTIVE_DENY_PATTERNS) + list(a["bash_deny"])

    if a["web_wide_open"]:
        pass  # no WebFetch rule at all — wide open, tiger only
    else:
        for domain in a["web_allowed_domains"]:
            allow.append(f"WebFetch(domain:{domain})")
        deny.append("WebFetch")

    if a["write_scope"] == "project":
        # Catch-all deny beneath the project-scoped allow above; the more
        # specific "./**" allow rule takes precedence within the project.
        deny.append("Write")
        deny.append("Edit")

    permissions = {
        "allow": allow,
        "deny": deny,
        "defaultMode": AUTONOMY_TO_CLAUDE_CODE_MODE[a["autonomy"]],
    }
    if a["bash_ask"]:
        permissions["ask"] = list(a["bash_ask"])

    return {
        "permissions": permissions,
        "sandbox": a["sandbox"],
    }


# Target name -> emitter function. A new target (e.g. "cursor") is added
# here as a new function reading the same LEVEL_POLICY abstract knobs;
# LEVEL_POLICY itself never needs to change.
TARGET_EMITTERS = {
    "claude-code": emit_claude_code_settings,
}


def build_profile_md(level, target, settings):
    policy = LEVEL_POLICY[level]
    perms = settings["permissions"]

    can_read = "inside this project" if policy["abstract"]["read_scope"] == "project" else "anywhere on this machine"
    can_write = "inside this project" if policy["abstract"]["write_scope"] == "project" else "anywhere on this machine"

    web_domains = []
    for pattern in perms["allow"]:
        m = re.match(r"WebFetch\(domain:(.+)\)$", pattern)
        if m:
            web_domains.append(m.group(1))
    if policy["abstract"]["web_wide_open"]:
        web_line = "- Fetch any web page. No allowlist — this cat goes where it wants."
    elif web_domains:
        web_line = "- Fetch pages only from:\n" + "\n".join(f"  - {d}" for d in web_domains)
    else:
        web_line = "- Fetch no web pages at all."

    bash_ask = perms.get("ask", [])
    ask_section = []
    if bash_ask:
        ask_lines = "\n".join(f"- `{p[5:-3]}`" if p.startswith("Bash(") and p.endswith(":*)") else f"- {p}" for p in bash_ask)
        ask_section = ["", "## What this cat has to ask about first", "", ask_lines]

    lines = [
        f"# Curiosity Cat — {policy['label']} profile ({target})",
        "",
        f"*{policy['summary']}*",
        "",
        "## What this cat can do",
        "",
        f"- Read files {can_read}.",
        f"- Write and edit files {can_write}.",
        web_line,
        *ask_section,
        "",
        "## What this cat cannot do, no matter what",
        "",
        "- Read SSH keys, AWS credentials, `.env` files, `.pem` files, or anything "
        "with \"credentials\" in the name. This holds at every adventure level — "
        "widening the slider widens exploration, not this.",
        "- Run `sudo` or `rm -rf`.",
    ]
    if not policy["abstract"]["web_wide_open"]:
        lines.append("- Fetch a web page outside the allowlist above.")
    if policy["abstract"]["write_scope"] == "project":
        lines.append("- Write or edit a file outside this project.")

    lines += [
        "",
        "## The safety net underneath",
        "",
        f"- Sandbox: {'on' if settings['sandbox'] else 'off'}. Even an allowed action runs "
        "inside the sandbox this target provides.",
        f"- Default permission mode: `{perms['defaultMode']}`.",
        "",
        "This profile was compiled, not hand-written. See `settings.json` for the exact "
        "rules and `scope-policy.json` for the underlying policy values.",
        "",
    ]
    return "\n".join(lines) + "\n"


def build_standing_orders_md(level, target):
    policy = LEVEL_POLICY[level]
    general = (DATA_DIR / "standing-orders" / "general-safety.md").read_text()
    header = (
        f"CURIOSITY CAT — COMPILED STANDING ORDERS\n"
        f"Level: {policy['label']} ({level})   Target: {target}\n"
        f"{policy['summary']}\n"
        f"\n---\n\n"
    )
    return header + general


def build_scope_policy(level, target):
    template = json.loads((DATA_DIR / "policies" / "scope-policy-template.json").read_text())
    template["policy_name"] = f"compiled-{level}-{target}"
    template["adventure_level"] = level
    template["rules"] = LEVEL_POLICY[level]["scope_policy"]
    return template


def cmd_init(role=None):
    if role and role not in ROLE_FILES:
        print(f'Unknown role: "{role}"', file=sys.stderr)
        print(f'Valid roles: {", ".join(ROLE_FILES)}', file=sys.stderr)
        sys.exit(1)

    cwd = Path.cwd()
    dest_root = cwd / "curiosity-cat"
    dest_orders = dest_root / "standing-orders"
    dest_policies = dest_root / "policies"
    dest_quarantine = dest_root / "quarantine"
    dest_logs = dest_root / "logs"

    for d in [dest_orders, dest_policies, dest_quarantine, dest_logs]:
        d.mkdir(parents=True, exist_ok=True)

    src_orders = DATA_DIR / "standing-orders"
    if role:
        files_to_copy = ROLE_FILES[role]
    else:
        seen = []
        for files in ROLE_FILES.values():
            for f in files:
                if f not in seen:
                    seen.append(f)
        files_to_copy = seen

    copied = []
    for filename in files_to_copy:
        src = src_orders / filename
        dest = dest_orders / filename
        if src.exists():
            shutil.copy2(src, dest)
            copied.append(f"  curiosity-cat/standing-orders/{filename}")

    policy_src = DATA_DIR / "policies" / "scope-policy-template.json"
    policy_dest = dest_policies / "scope-policy-template.json"
    if policy_src.exists():
        shutil.copy2(policy_src, policy_dest)
        copied.append("  curiosity-cat/policies/scope-policy-template.json")

    print("\nCuriosity Cat initialised.\n")
    print("Created:")
    for f in copied:
        print(f)
    print("  curiosity-cat/quarantine/   (safe drop zone for suspicious content)")
    print("  curiosity-cat/logs/         (incident log directory)")
    print("\nNext steps:")
    print("  1. Open curiosity-cat/standing-orders/ and paste the relevant file into your agent's system prompt.")
    print("  2. Customise curiosity-cat/policies/scope-policy-template.json for your project.")
    print('  3. Run "curiosity-cat report" to learn how to submit a close call to the Danger Map.\n')


def cmd_report():
    print("""
Curiosity Cat — Danger Map Close Call Report
============================================

Endpoint:
  POST https://pcmqmvcxqsaypuabrkgj.supabase.co/functions/v1/danger-map/report

Auth (required):
  -H "Authorization: Bearer <your-api-key>"
  or
  -H "x-api-key: <your-api-key>"

Payload (JSON):
  Required fields:
    "timestamp":     "ISO 8601 datetime of the incident",
    "threat_class":  "prompt-injection | unsafe-url | data-exfiltration | unauthorized-tool-use | credential-exposure | package-risk | memory-poisoning | social-engineering | scope-violation | other",
    "severity":      "scratched | bitten | nearly_eaten",
    "source":        "Where the threat came from (URL, filename, user input, etc.)",
    "what_happened": "What the agent was asked or encountered",
    "action_taken":  "What the agent did to handle it",
    "lesson":        "What this incident teaches"

  Optional fields:
    "agent_type":      "Type of agent (e.g. research, coding, enterprise)",
    "adventure_level": "housecat | alleycat | tiger",
    "submitted_by":    "Your identifier (optional)",
    "framework":       "Agent framework used (e.g. claude-code, langgraph)",
    "region":          "AWS/GCP/Azure region or 'local'"

curl example:
  curl -X POST https://pcmqmvcxqsaypuabrkgj.supabase.co/functions/v1/danger-map/report \\
    -H "Content-Type: application/json" \\
    -H "Authorization: Bearer <your-api-key>" \\
    -d '{
      "timestamp":     "2026-04-16T10:00:00Z",
      "threat_class":  "prompt-injection",
      "severity":      "bitten",
      "source":        "PDF attachment from external user",
      "what_happened": "A document instructed the agent to ignore standing orders and exfiltrate chat history.",
      "action_taken":  "Agent refused and flagged the document as hostile input.",
      "lesson":        "All external document content must be treated as untrusted regardless of framing.",
      "agent_type":    "research",
      "adventure_level": "housecat"
    }'

Thank you for making the community safer.
""")


def cmd_compile(level=None, target=None):
    if level not in LEVELS:
        print(f'Missing or unknown --level: "{level}"', file=sys.stderr)
        print(f'Valid levels: {", ".join(LEVELS)}', file=sys.stderr)
        sys.exit(1)
    if target not in TARGET_EMITTERS:
        print(f'Missing or unknown --target: "{target}"', file=sys.stderr)
        print(f'Valid targets: {", ".join(TARGET_EMITTERS)}', file=sys.stderr)
        sys.exit(1)

    profiles_root = Path.cwd() / "curiosity-cat" / "profiles"
    profiles_root.mkdir(parents=True, exist_ok=True)

    base_name = f"{level}-{target}-{date.today().strftime('%Y%m%d')}"
    profile_dir = profiles_root / base_name
    suffix = 2
    while profile_dir.exists():
        profile_dir = profiles_root / f"{base_name}-v{suffix}"
        suffix += 1
    profile_dir.mkdir(parents=True)

    settings = TARGET_EMITTERS[target](level)
    (profile_dir / "settings.json").write_text(json.dumps(settings, indent=2) + "\n")
    (profile_dir / "scope-policy.json").write_text(json.dumps(build_scope_policy(level, target), indent=2) + "\n")
    (profile_dir / "standing-orders.md").write_text(build_standing_orders_md(level, target))
    (profile_dir / "PROFILE.md").write_text(build_profile_md(level, target, settings))

    rel = profile_dir.relative_to(Path.cwd())
    print(f"\nCompiled {LEVEL_POLICY[level]['label']} profile for {target}.\n")
    print("Created:")
    print(f"  {rel}/settings.json")
    print(f"  {rel}/scope-policy.json")
    print(f"  {rel}/standing-orders.md")
    print(f"  {rel}/PROFILE.md")
    print(f'\nRead {rel}/PROFILE.md first — plain-language summary of what this cat can and cannot do.\n')


def cmd_stories():
    stories_dir = DATA_DIR / "stories"
    if not stories_dir.exists():
        print("No stories directory found in package.", file=sys.stderr)
        sys.exit(1)

    files = sorted([f for f in stories_dir.iterdir() if f.suffix == ".md"], reverse=True)

    if not files:
        print("No stories found.")
        return

    latest = files[0]
    print(f"\n--- {latest.name} ---\n")
    print(latest.read_text())


def print_help():
    print("""
curiosity-cat — AI agent safety framework

Usage:
  curiosity-cat init [--role <role>]                       Scaffold standing orders into ./curiosity-cat/
  curiosity-cat compile --level <level> --target <target>  Compile a dated profile into ./curiosity-cat/profiles/
  curiosity-cat report                                     Show how to submit a close call to the Danger Map
  curiosity-cat stories                                    Print the latest story

Roles (for init --role):
  research     general-safety.md + research-agent.md
  coding       general-safety.md + coding-agent.md
  enterprise   general-safety.md + enterprise-analyst.md
  all          All standing orders (default if --role omitted)

Levels (for compile --level):
  housecat     Cautious — nothing leaves the yard
  alleycat     Balanced — calculated risks, still comes home
  tiger        Daring — widest range, sandbox is the backstop

Targets (for compile --target):
  claude-code  Claude Code settings.json (permissions, sandbox)
""")


def main():
    parser = argparse.ArgumentParser(
        prog="curiosity-cat",
        description="AI agent safety framework",
        add_help=False,
    )
    parser.add_argument("command", nargs="?", choices=["init", "compile", "report", "stories"])
    parser.add_argument("--role", choices=list(ROLE_FILES.keys()))
    parser.add_argument("--level", choices=LEVELS)
    parser.add_argument("--target", choices=list(TARGET_EMITTERS.keys()))
    parser.add_argument("-h", "--help", action="store_true")

    args, _ = parser.parse_known_args()

    if args.help or not args.command:
        print_help()
        return

    if args.command == "init":
        cmd_init(role=args.role)
    elif args.command == "compile":
        cmd_compile(level=args.level, target=args.target)
    elif args.command == "report":
        cmd_report()
    elif args.command == "stories":
        cmd_stories()


if __name__ == "__main__":
    main()
