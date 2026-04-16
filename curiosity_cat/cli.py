#!/usr/bin/env python3
"""curiosity-cat CLI — AI agent safety framework."""

import argparse
import os
import shutil
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

ROLE_FILES = {
    "research":   ["general-safety.md", "research-agent.md"],
    "coding":     ["general-safety.md", "coding-agent.md"],
    "enterprise": ["general-safety.md", "enterprise-analyst.md"],
    "all":        ["general-safety.md", "research-agent.md", "coding-agent.md", "enterprise-analyst.md"],
}


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
  curiosity-cat init [--role <role>]   Scaffold standing orders into ./curiosity-cat/
  curiosity-cat report                 Show how to submit a close call to the Danger Map
  curiosity-cat stories                Print the latest story

Roles (for init --role):
  research     general-safety.md + research-agent.md
  coding       general-safety.md + coding-agent.md
  enterprise   general-safety.md + enterprise-analyst.md
  all          All standing orders (default if --role omitted)
""")


def main():
    parser = argparse.ArgumentParser(
        prog="curiosity-cat",
        description="AI agent safety framework",
        add_help=False,
    )
    parser.add_argument("command", nargs="?", choices=["init", "report", "stories"])
    parser.add_argument("--role", choices=list(ROLE_FILES.keys()))
    parser.add_argument("-h", "--help", action="store_true")

    args, _ = parser.parse_known_args()

    if args.help or not args.command:
        print_help()
        return

    if args.command == "init":
        cmd_init(role=args.role)
    elif args.command == "report":
        cmd_report()
    elif args.command == "stories":
        cmd_stories()


if __name__ == "__main__":
    main()
