#!/usr/bin/env python3
"""curiosity-cat CLI — AI agent safety framework.

A thin argparse wrapper over curiosity_cat.core: this module owns argument
parsing, human-readable printing, and exit codes; core owns the actual
compile/prove/check/report_close_call logic.
"""

import argparse
import shutil
import sys
from pathlib import Path

from curiosity_cat import core

DATA_DIR = core.DATA_DIR
ROLE_FILES = core.ROLE_FILES
LEVELS = core.LEVELS
TARGET_EMITTERS = core.TARGET_EMITTERS


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
    print(core.DANGER_MAP_REPORT_HELP)


def cmd_compile(level=None, target=None):
    try:
        profile = core.compile_profile(level, target)
    except core.InvalidLevelError:
        print(f'Missing or unknown --level: "{level}"', file=sys.stderr)
        print(f'Valid levels: {", ".join(LEVELS)}', file=sys.stderr)
        sys.exit(1)
    except core.InvalidTargetError:
        print(f'Missing or unknown --target: "{target}"', file=sys.stderr)
        print(f'Valid targets: {", ".join(TARGET_EMITTERS)}', file=sys.stderr)
        sys.exit(1)

    profile_dir = Path(profile.path)
    rel = profile_dir.relative_to(Path.cwd())
    print(f"\nCompiled {core.LEVEL_POLICY[level]['label']} profile for {target}.\n")
    print("Created:")
    print(f"  {rel}/settings.json")
    print(f"  {rel}/scope-policy.json")
    print(f"  {rel}/standing-orders.md")
    print(f"  {rel}/PROFILE.md")
    print(f'\nRead {rel}/PROFILE.md first — plain-language summary of what this cat can and cannot do.\n')


def cmd_prove(profile=None, observed=None):
    if not profile:
        print('Missing --profile <profile-dir>', file=sys.stderr)
        sys.exit(1)

    try:
        clean_bill = core.prove(profile, observed=observed)
    except core.InvalidProfileError:
        print(f'"{profile}" does not look like a compiled profile directory '
              '(missing settings.json or scope-policy.json).', file=sys.stderr)
        sys.exit(1)

    proof_dir = Path(clean_bill.proof_dir)
    try:
        rel = proof_dir.relative_to(Path.cwd())
    except ValueError:
        rel = proof_dir
    failed = [t for t in clean_bill.self_consistency_trials + clean_bill.observed_trials
              if t.get("held") is False]

    print(f"\nRan {len(clean_bill.self_consistency_trials)} self-consistency trial(s), "
          f"{len(clean_bill.observed_trials)} observed (live) trial(s), and noted "
          f"{len(clean_bill.guidance_only)} guidance-only item(s) against {profile}.")
    if clean_bill.observed_note:
        print(clean_bill.observed_note)
    print("\nWrote:")
    print(f"  {rel}/clean-bill.json")
    print(f"  {rel}/CLEAN-BILL.md")

    if failed:
        print(f"\n{len(failed)} wall(s) did NOT hold:", file=sys.stderr)
        for t in failed:
            print(f"  - {t['trial']} ({t['method']}): expected {t['expected']}, "
                  f"observed {t.get('observed', 'allowed')}", file=sys.stderr)
        print("\nNo safe claim.", file=sys.stderr)
        sys.exit(1)

    print(f"\nAll {len(clean_bill.self_consistency_trials) + len(clean_bill.observed_trials)} "
          "tested walls held. Clean bill of health.\n")


def cmd_check(candidate=None):
    if not candidate:
        print('Missing candidate — usage: curiosity-cat check <url-or-source>', file=sys.stderr)
        sys.exit(1)

    verdict = core.check(candidate)
    print(f"\nWhisker check — {candidate}")
    print(f"Checked: {verdict.checked_at}")
    if verdict.note:
        print(verdict.note)
    if verdict.matched:
        print(f"\n{len(verdict.matches)} matching Danger Map incident(s) found:")
        for m in verdict.matches:
            print(f"  - {m}")
    else:
        print("\nNo matching Danger Map incidents found.")


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
  curiosity-cat prove --profile <profile-dir> [--no-observed]
                                                             Run escape trials against a compiled profile
  curiosity-cat check <candidate>                          Look up a URL/source against the Danger Map
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

Prove:
  --profile <dir>  A directory produced by "curiosity-cat compile"
  --no-observed    Skip the observed trial (a real, non-interactive Claude Code
                   session spawned in a throwaway sandbox to attempt one denied
                   action for real). On by default when a `claude` binary is on
                   PATH; skipped with a note otherwise.

Check:
  <candidate>      A URL, domain, or other source string to look up against
                   the community Danger Map's recent close calls.
""")


def main():
    parser = argparse.ArgumentParser(
        prog="curiosity-cat",
        description="AI agent safety framework",
        add_help=False,
    )
    parser.add_argument("command", nargs="?", choices=["init", "compile", "prove", "check", "report", "stories"])
    parser.add_argument("candidate", nargs="?")
    parser.add_argument("--role", choices=list(ROLE_FILES.keys()))
    parser.add_argument("--level", choices=LEVELS)
    parser.add_argument("--target", choices=list(TARGET_EMITTERS.keys()))
    parser.add_argument("--profile")
    parser.add_argument("--no-observed", action="store_true")
    parser.add_argument("-h", "--help", action="store_true")

    args, _ = parser.parse_known_args()

    if args.help or not args.command:
        print_help()
        return

    if args.command == "init":
        cmd_init(role=args.role)
    elif args.command == "compile":
        cmd_compile(level=args.level, target=args.target)
    elif args.command == "prove":
        cmd_prove(profile=args.profile, observed=(False if args.no_observed else None))
    elif args.command == "check":
        cmd_check(candidate=args.candidate)
    elif args.command == "report":
        cmd_report()
    elif args.command == "stories":
        cmd_stories()


if __name__ == "__main__":
    main()
