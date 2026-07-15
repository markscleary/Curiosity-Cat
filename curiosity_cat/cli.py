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

from curiosity_cat import card, core, discover, listen, purr

DATA_DIR = core.DATA_DIR
ROLE_FILES = core.ROLE_FILES
LEVELS = core.LEVELS
TARGET_EMITTERS = core.TARGET_EMITTERS


def cmd_init(role=None):
    if role and role not in ROLE_FILES:
        print(f'Unknown role: "{role}"', file=sys.stderr)
        print(f'Valid roles: {", ".join(ROLE_FILES)}', file=sys.stderr)
        sys.exit(1)

    dest_root = core.resolve_home()
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
            copied.append(f"  {dest}")

    policy_src = DATA_DIR / "policies" / "scope-policy-template.json"
    policy_dest = dest_policies / "scope-policy-template.json"
    if policy_src.exists():
        shutil.copy2(policy_src, policy_dest)
        copied.append(f"  {policy_dest}")

    print(f"\nCuriosity Cat initialised at {dest_root}\n")
    print("Created:")
    for f in copied:
        print(f)
    print(f"  {dest_quarantine}   (safe drop zone for suspicious content)")
    print(f"  {dest_logs}         (incident log directory)")
    print("\nNext steps:")
    print(f"  1. Open {dest_orders} and paste the relevant file into your agent's system prompt.")
    print(f"  2. Customise {policy_dest} for your project.")
    print('  3. Run "curiosity-cat report" to learn how to submit a close call to the Danger Map.\n')


def cmd_report():
    print(core.DANGER_MAP_REPORT_HELP)


def cmd_compile(level=None, target=None, profiles_dir=None):
    try:
        profile = core.compile_profile(level, target, profiles_dir=profiles_dir)
    except core.InvalidLevelError:
        print(f'Missing or unknown --level: "{level}"', file=sys.stderr)
        print(f'Valid levels: {", ".join(LEVELS)}', file=sys.stderr)
        sys.exit(1)
    except core.InvalidTargetError:
        print(f'Missing or unknown --target: "{target}"', file=sys.stderr)
        print(f'Valid targets: {", ".join(TARGET_EMITTERS)}', file=sys.stderr)
        sys.exit(1)

    profile_dir = Path(profile.path)
    print(f"\nCompiled {core.LEVEL_POLICY[level]['label']} profile for {target}.\n")
    print(f"Profiles live at: {profile_dir.parent}\n")
    print("Created:")
    print(f"  {profile_dir / 'settings.json'}")
    print(f"  {profile_dir / 'scope-policy.json'}")
    print(f"  {profile_dir / 'standing-orders.md'}")
    print(f"  {profile_dir / 'PROFILE.md'}")
    print(f"  {profile_dir / 'manifest.json'}")
    print(f"\nRead {profile_dir / 'PROFILE.md'} first — plain-language summary of what this cat can and cannot do.\n")
    print("This profile is not yet assigned to any target. It protects nothing until it is "
          "applied — run \"curiosity-cat estate\" to see what's out there to protect.\n")


def _protection_summary_lines(level, target_label, applied_at):
    """The Assignment Model's three-question answer (docs/app/APP_SPEC.md):
    what is now protected, from what, since when. Every apply-time
    protection claim this CLI prints goes through here so none of them can
    drift into a bare "protected" with no level, wall list, or date.
    """
    policy = core.LEVEL_POLICY[level]
    abstract = policy["abstract"]

    walls = ["credential files (.env, .pem, SSH/AWS keys)", "destructive commands (sudo, rm -rf)"]
    bash_cmds = [p[5:-3] for p in abstract["bash_deny"] if p.startswith("Bash(") and p.endswith(":*)")]
    if bash_cmds:
        walls.append(f"{', '.join(bash_cmds)} (denied outright at this level)")
    if not abstract["web_wide_open"] and abstract["web_allowed_domains"]:
        walls.append(f"web fetches outside {len(abstract['web_allowed_domains'])} allow-listed domain(s)")
    if abstract["write_scope"] == "project":
        walls.append("writes/edits outside this project")

    return [
        f"What is now protected: {target_label} — {policy['label']} ({level}) profile applied.",
        f"From what: {'; '.join(walls)}.",
        f"Since when: {applied_at}.",
    ]


def cmd_apply(level=None, target=None, observed=None):
    if not level or level not in LEVELS:
        print(f'Missing or unknown --level: "{level}"', file=sys.stderr)
        print(f'Valid levels: {", ".join(LEVELS)}', file=sys.stderr)
        sys.exit(1)
    if not target:
        print('Missing --target <path|global>', file=sys.stderr)
        sys.exit(1)

    profile = core.compile_profile(level, "claude-code")
    apply_result = core.apply(profile.path, target)

    print(f"\nApplied {core.LEVEL_POLICY[level]['label']} profile to {apply_result.target}.\n")
    print(f"  {apply_result.settings_path}")
    if apply_result.backup_path:
        print(f"  Backed up prior settings to: {apply_result.backup_path}")
    print("\nWhat was merged:" if apply_result.merged else "\nInstalled:")
    for line in apply_result.merge_report:
        print(f"  - {line}")

    try:
        clean_bill = core.prove(profile.path, observed=observed, target=target)
    except core.TargetNotAppliedError as exc:
        print(f"\nProve failed: {exc}", file=sys.stderr)
        sys.exit(1)

    failed = [t for t in clean_bill.self_consistency_trials + clean_bill.observed_trials
              if t.get("held") is False]

    print(f"\nRan {len(clean_bill.self_consistency_trials)} self-consistency trial(s) and "
          f"{len(clean_bill.observed_trials)} observed (live) trial(s) against {apply_result.target}.")
    if clean_bill.observed_note:
        print(clean_bill.observed_note)

    print()
    for line in _protection_summary_lines(level, apply_result.target, apply_result.applied_at):
        print(line)
    print(f"\n  {clean_bill.clean_bill_md_path}\n")

    if failed:
        print(f"{len(failed)} wall(s) did NOT hold — see the Clean Bill above for detail.\n", file=sys.stderr)
        sys.exit(1)


def cmd_unapply(target=None):
    if not target:
        print('Missing --target <path|global>', file=sys.stderr)
        sys.exit(1)

    try:
        result = core.unapply(target)
    except core.TargetNotAppliedError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    print(f"\nUnapplied {result.target}.")
    print(f"  {result.note}\n")


def _fleet_applicable_targets(inventory):
    """Discovered targets apply_many() can actually install into: a Claude
    Code project directory, or the literal "global" for the operator's own
    settings. Agent-workspace and MCP-server targets are real, discovered
    targets too (curiosity-cat estate), but neither has a settings.json of
    its own for apply() to write into, so Fleet mode only ever touches the
    two kinds it can act on.
    """
    targets = []
    for t in inventory.targets:
        if t.kind == "claude-code-project":
            targets.append(t.path)
        elif t.kind == "claude-code-global":
            targets.append(core.GLOBAL_TARGET)
    return targets


def cmd_fleet(level=None, observed=None, undo=False):
    if undo:
        result = core.unapply_many()
        print(f"\nFleet undo — {len(result.outcomes)} target(s), {result.date}.\n")
        for o in result.outcomes:
            if o.ok:
                print(f"  [ok]     {o.target} — {o.unapply_result.note}")
            else:
                print(f"  [FAILED] {o.target} — {o.error}")
        print(f"\n{result.restored} restored, {result.failed} failed.\n")
        if result.failed:
            sys.exit(1)
        return

    if not level or level not in LEVELS:
        print(f'Missing or unknown --level: "{level}"', file=sys.stderr)
        print(f'Valid levels: {", ".join(LEVELS)}', file=sys.stderr)
        sys.exit(1)

    inventory = discover.build_inventory()
    targets = _fleet_applicable_targets(inventory)
    if not targets:
        print('\nNo applicable targets found — nothing to protect. Run "curiosity-cat estate" '
              "to see what's out there.\n", file=sys.stderr)
        sys.exit(1)

    print(f"\nProtecting whole fleet — {len(targets)} target(s) at "
          f"{core.LEVEL_POLICY[level]['label']} level. Backing up each target's existing settings first.\n")
    for t in targets:
        print(f"  - {t}")

    result = core.apply_many(level, targets, observed=observed)

    print(f"\nApplied and proved {len(result.outcomes)} target(s):")
    for o in result.outcomes:
        if o.ok:
            status = "clean bill" if o.clean_bill.passed else "applied, but findings — see its Clean Bill"
            print(f"  [ok]     {o.target} — {status}")
        else:
            print(f"  [FAILED] {o.target} — {o.error}")

    print(f"\nFleet Clean Bill — {result.agents_proven} of {len(result.outcomes)} target(s) proven clean, "
          f"{result.walls_proven} wall(s) held, {result.date}.")
    print(f"  {result.fleet_clean_bill_md_path}\n")

    if result.agents_failed:
        print(f"{result.agents_failed} target(s) did not come back with a clean bill — see above.\n",
              file=sys.stderr)
        sys.exit(1)


def cmd_prove(profile=None, observed=None, target=None):
    if not profile:
        print('Missing --profile <profile-dir>', file=sys.stderr)
        sys.exit(1)

    try:
        clean_bill = core.prove(profile, observed=observed, target=target)
    except core.InvalidProfileError:
        print(f'"{profile}" does not look like a compiled profile directory '
              '(missing settings.json or scope-policy.json).', file=sys.stderr)
        sys.exit(1)
    except core.TargetNotAppliedError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    proof_dir = Path(clean_bill.proof_dir)
    failed = [t for t in clean_bill.self_consistency_trials + clean_bill.observed_trials
              if t.get("held") is False]

    against = clean_bill.applied_target or profile
    print(f"\nRan {len(clean_bill.self_consistency_trials)} self-consistency trial(s), "
          f"{len(clean_bill.observed_trials)} observed (live) trial(s), and noted "
          f"{len(clean_bill.guidance_only)} guidance-only item(s) against {against}.")
    if clean_bill.observed_note:
        print(clean_bill.observed_note)
    print("\nWrote:")
    print(f"  {proof_dir / 'clean-bill.json'}")
    print(f"  {proof_dir / 'CLEAN-BILL.md'}")

    if failed:
        print(f"\n{len(failed)} wall(s) did NOT hold:", file=sys.stderr)
        for t in failed:
            print(f"  - {t['trial']} ({t['method']}): expected {t['expected']}, "
                  f"observed {t.get('observed', 'allowed')}", file=sys.stderr)
        print("\nNo safe claim.", file=sys.stderr)
        sys.exit(1)

    print(f"\nAll {len(clean_bill.self_consistency_trials) + len(clean_bill.observed_trials)} "
          "tested walls held. Clean bill of health.\n")


def cmd_card(clean_bill_path=None, out=None):
    if not clean_bill_path:
        print('Missing <clean-bill.json> — usage: curiosity-cat card <clean-bill.json> [--out PATH]',
              file=sys.stderr)
        sys.exit(1)

    path = Path(clean_bill_path)
    if not path.exists():
        print(f'"{clean_bill_path}" does not exist.', file=sys.stderr)
        sys.exit(1)

    written = card.render_share_card_from_file(path, out_path=out)
    print(f"\nWrote share card: {written}\n")


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


def _parse_ids(raw):
    try:
        return [int(part) for part in raw.split(",") if part.strip()]
    except ValueError:
        print(f'--approve expects comma-separated numeric ids, got "{raw}"', file=sys.stderr)
        sys.exit(1)


def cmd_tray(profile=None, approve=None):
    if not profile:
        print('Missing --profile <profile-dir>', file=sys.stderr)
        sys.exit(1)

    if approve is not None:
        ids = _parse_ids(approve)
        results = core.submit_approved(profile, ids)
        print()
        ok = True
        for r in results:
            status = "submitted" if r["submitted"] else "NOT submitted"
            print(f"  [{r['id']}] {status} — {r['reason']}")
            if not r["submitted"]:
                ok = False
        print()
        if not ok:
            sys.exit(1)
        return

    queue = core.list_tray(profile)
    if not queue:
        print("\n🐭 Mouse Tray — empty. Nothing waiting for your look.\n")
        return

    pending = [r for r in queue if r["status"] == "pending"]
    print(f"\n🐭 Mouse Tray — {len(pending)} item(s) awaiting your look "
          f"({len(queue) - len(pending)} already submitted)\n")
    for r in queue:
        e = r["event"]
        pattern = e.get("indicator") or e.get("source", "?")
        print(f"  [{r['id']}] {r['status']:<9} {r['queued_at']}  "
              f"This cat flagged `{pattern}` as {e.get('threat_class', '?')} ({e.get('grade', '?')}).")

    if pending:
        ids_hint = ",".join(str(r["id"]) for r in pending)
        print(f"\nNothing leaves this machine until you approve it: "
              f"curiosity-cat tray --approve {ids_hint}\n")
    else:
        print()


def cmd_vet(profile=None, recompile=False):
    if not profile:
        print('Missing --profile <profile-dir>', file=sys.stderr)
        sys.exit(1)

    try:
        report = core.vet(profile, recompile=recompile)
    except core.InvalidProfileError:
        print(f'"{profile}" does not look like a compiled profile directory '
              '(missing manifest.json or scope-policy.json).', file=sys.stderr)
        sys.exit(1)

    print(f"\nVet — {profile}\n")
    print(f"  {report.profile_axis}")
    print(f"  {report.danger_map_axis}")
    print(f"  {report.platform_axis}")

    if report.drift_signals:
        print("\nDrift signal — a wall's verdict changed across platform versions:")
        for d in report.drift_signals:
            verdicts = ", ".join(f"{verdict} on {pv}" for pv, verdict in d["verdicts"].items())
            print(f"  - {d['wall']}: {verdicts}")

    if report.recompiled:
        cb = report.new_clean_bill
        print(f"\nRecompiled and proved a fresh profile: {cb.profile_dir}")
        print(f"  {cb.clean_bill_md_path}")
        if not cb.passed:
            print("  Some walls did NOT hold in the fresh proof — see the Clean Bill for detail.",
                  file=sys.stderr)
    print()


def cmd_listen(profile=None):
    if not profile:
        print('Missing --profile <profile-dir>', file=sys.stderr)
        sys.exit(1)
    listen.serve_forever(profile)


def cmd_purr(profile=None, days=None):
    if not profile:
        print('Missing --profile <profile-dir>', file=sys.stderr)
        sys.exit(1)
    print()
    print(purr.generate_purr(profile, days=days or purr.DEFAULT_WINDOW_DAYS))
    print()


_ESTATE_KIND_LABELS = [
    ("claude-code-project", "Claude Code projects"),
    ("claude-code-global", "Claude Code global settings"),
    ("agent-process", "Agent workspaces"),
    ("mcp-server", "MCP servers"),
]


def cmd_estate():
    inventory = discover.build_inventory()
    print(f"\nCuriosity Cat — Estate ({len(inventory.targets)} target(s) found, "
          f"discovered {inventory.discovered_at})\n")

    if not inventory.targets:
        print("No protectable surfaces found. That means nothing here is protected because "
              f"nothing here was found — widen the search with ${discover.DISCOVER_ROOTS_ENV} "
              "if this looks wrong.\n")
        return

    by_kind = {}
    for t in inventory.targets:
        by_kind.setdefault(t.kind, []).append(t)

    for kind, label in _ESTATE_KIND_LABELS:
        targets = by_kind.get(kind)
        if not targets:
            continue
        print(f"{label}:")
        for t in targets:
            extra = ""
            if kind == "agent-process":
                extra = "  (running now)" if t.detail.get("running") else "  (not running)"
            elif kind == "mcp-server":
                extra = f"  ({t.detail.get('scope')})"
            print(f"  {discover.format_protection(t.protection)} — {t.label}{extra}")
        print()

    if inventory.worst_state == discover.GUARDED:
        print("Worst protection state across this estate: GUARDED — every target here has an applied profile.\n")
    else:
        print("Worst protection state across this estate: UNGUARDED — at least one target here has "
              "no profile applied. The tray icon shows this worst case, not the best one.\n")


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
  curiosity-cat init [--role <role>]                       Scaffold standing orders
  curiosity-cat compile --level <level> --target <target> [--profiles-dir <dir>]
                                                             Compile a dated profile
  curiosity-cat prove --profile <profile-dir> [--no-observed] [--target <path|global>]
                                                             Run escape trials against a compiled profile
  curiosity-cat apply --level <level> --target <path|global> [--no-observed]
                                                             Compile, apply, and prove in one motion
  curiosity-cat unapply --target <path|global>              Undo apply — restore the pre-apply backup
  curiosity-cat fleet --level <level> [--no-observed]        Discover every target, apply and prove
                                                             <level> to all of them in one motion
  curiosity-cat fleet --undo                                Undo-all — restore every currently guarded
                                                             target's pre-apply backup
  curiosity-cat check <candidate>                          Look up a URL/source against the Danger Map
  curiosity-cat report                                     Show how to submit a close call to the Danger Map
  curiosity-cat tray --profile <profile-dir> [--approve <ids>]
                                                             List or approve the Mouse Tray queue
  curiosity-cat vet --profile <profile-dir> [--recompile]  Compare a profile against what's installed now
  curiosity-cat listen --profile <profile-dir>             Run the reference Watcher listener
  curiosity-cat card <clean-bill.json> [--out <path>]      Render a Clean Bill share card PNG
  curiosity-cat purr --profile <profile-dir> [--days <n>]  Print this week's Purr digest
  curiosity-cat stories                                    Print the latest story
  curiosity-cat estate                                     Show every protectable target and its state

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

Where profiles live:
  By default, curiosity-cat writes profiles/, standing-orders/, policies/,
  quarantine/, and logs/ under a resolved "home" directory. In order:
    1. --profiles-dir <dir>      (compile only — used exactly as given)
    2. $CURIOSITY_CAT_HOME       (env var — sets the whole home directory)
    3. ./curiosity-cat           (if it already exists and cwd is writable)
    4. ~/Library/Application Support/Curiosity Cat  (macOS default)
  The resolved location is always printed after compile/init.

Prove:
  --profile <dir>  A directory produced by "curiosity-cat compile"
  --no-observed    Skip the observed trial (a real, non-interactive Claude Code
                   session spawned in a throwaway sandbox to attempt one denied
                   action for real). On by default when a `claude` binary is on
                   PATH; skipped with a note otherwise.
  --target <path|global>
                   Prove against a target's real, applied settings.json instead
                   of the profile directory in isolation — requires "apply" to
                   have already run against this target. The Clean Bill records
                   the target proved, and the target's registry entry gets its
                   proof date stamped.

Apply:
  --level <level>  Which adventure level to compile and apply (see Levels below).
  --target <path|global>
                   Where to install it: a Claude Code project directory, or the
                   literal word "global" for ~/.claude/settings.json.
  --no-observed    Passed through to the prove step (see Prove above).
  Compiles a fresh profile, installs it into the target's real settings.json
  (always backing up whatever was there first, merging conservatively if
  anything was), then proves it live against that target. Prints the
  three-question summary: what is now protected, from what, since when.

Unapply:
  --target <path|global>
                   The target to restore — same values as "apply --target".
  Restores the target's pre-apply settings.json from its backup (or removes
  it, if there was nothing there before) and clears the registry entry.

Fleet:
  --level <level>  Which adventure level to compile and apply to every
                   discovered target (see Levels below).
  --no-observed    Passed through to each target's prove step (see Prove above).
  --undo           Undo the whole fleet instead — restores every currently
                   guarded target's pre-apply backup and clears its registry
                   entry. Ignores --level.
  Runs "curiosity-cat estate" discovery, then applies and proves <level>
  against every Claude Code project and the global settings it finds —
  same backup-and-merge guarantees as a single "apply", once per target.
  One target failing never stops the rest; the summary and a fleet-wide
  Clean Bill (fleet-clean-bill.json / FLEET-CLEAN-BILL.md) report every
  target's own outcome.

Check:
  <candidate>      A URL, domain, or other source string to look up against
                   the community Danger Map's recent close calls.

Tray:
  --profile <dir>  A directory produced by "curiosity-cat compile"
  --approve <ids>  Comma-separated Mouse Tray ids to submit to the Danger Map.
                   With no --approve, lists the queue instead. Nothing is
                   ever submitted without an explicit --approve.

Vet:
  --profile <dir>    A directory produced by "curiosity-cat compile"
  --recompile        Recompile a fresh, separately-dated profile for the
                     same level/target and prove it (observed trials),
                     emitting a new Clean Bill. Without this flag, vet is
                     read-only and never writes anything.

Listen:
  --profile <dir>  A directory produced by "curiosity-cat compile" — denied
                   events with a threat_class are queued to this profile's
                   Mouse Tray. Listens on 127.0.0.1:8377/event, the same
                   endpoint compiled PreToolUse/PostToolUse hooks POST to.

Card:
  <clean-bill.json>  Path to a clean-bill.json written by "curiosity-cat prove"
  --out <path>        Where to write the PNG. Defaults to share-card.png
                       alongside the clean-bill.json.

Purr:
  --profile <dir>  A directory produced by "curiosity-cat compile"
  --days <n>       How many days of event history/Mouse Tray to summarise
                    (default 7)

Estate:
  Prints every protectable target this machine has — Claude Code project
  directories, the global ~/.claude settings, running agent processes, and
  configured MCP servers — each with its current, honest protection state.
  A compiled profile protects nothing until it's applied to a target (see
  docs/app/APP_SPEC.md's Assignment Model), so every target here reads
  UNGUARDED until "curiosity-cat apply --target <path>" has run against it.
  Override the project-search roots with $CURIOSITY_CAT_DISCOVER_ROOTS
  (a PATH-style, colon-separated list) — default is your home directory.
""")


def main():
    parser = argparse.ArgumentParser(
        prog="curiosity-cat",
        description="AI agent safety framework",
        add_help=False,
    )
    parser.add_argument("command", nargs="?",
                         choices=["init", "compile", "prove", "apply", "unapply", "fleet", "check", "report",
                                  "tray", "vet", "listen", "card", "purr", "stories", "estate"])
    parser.add_argument("candidate", nargs="?")
    parser.add_argument("--role", choices=list(ROLE_FILES.keys()))
    parser.add_argument("--level", choices=LEVELS)
    # No `choices=` here: compile's --target names a platform emitter
    # ("claude-code", validated below via core.InvalidTargetError), but
    # apply's/unapply's/prove's --target names an Assignment Model
    # location — an arbitrary project path, or "global" — which argparse
    # choices can't express. Each command validates what it needs.
    parser.add_argument("--target")
    parser.add_argument("--profile")
    parser.add_argument("--profiles-dir")
    parser.add_argument("--no-observed", action="store_true")
    parser.add_argument("--undo", action="store_true")
    parser.add_argument("--approve")
    parser.add_argument("--recompile", action="store_true")
    parser.add_argument("--out")
    parser.add_argument("--days", type=int)
    parser.add_argument("-h", "--help", action="store_true")

    args, _ = parser.parse_known_args()

    if args.help or not args.command:
        print_help()
        return

    if args.command == "init":
        cmd_init(role=args.role)
    elif args.command == "compile":
        cmd_compile(level=args.level, target=args.target, profiles_dir=args.profiles_dir)
    elif args.command == "prove":
        cmd_prove(profile=args.profile, observed=(False if args.no_observed else None), target=args.target)
    elif args.command == "apply":
        cmd_apply(level=args.level, target=args.target, observed=(False if args.no_observed else None))
    elif args.command == "unapply":
        cmd_unapply(target=args.target)
    elif args.command == "fleet":
        cmd_fleet(level=args.level, observed=(False if args.no_observed else None), undo=args.undo)
    elif args.command == "check":
        cmd_check(candidate=args.candidate)
    elif args.command == "report":
        cmd_report()
    elif args.command == "tray":
        cmd_tray(profile=args.profile, approve=args.approve)
    elif args.command == "vet":
        cmd_vet(profile=args.profile, recompile=args.recompile)
    elif args.command == "listen":
        cmd_listen(profile=args.profile)
    elif args.command == "card":
        cmd_card(clean_bill_path=args.candidate, out=args.out)
    elif args.command == "purr":
        cmd_purr(profile=args.profile, days=args.days)
    elif args.command == "stories":
        cmd_stories()
    elif args.command == "estate":
        cmd_estate()


if __name__ == "__main__":
    main()
