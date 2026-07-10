# Draft — optional upstream report for Anthropic

Not filed. Draft only, for Mark to review/edit/send at his discretion.

**This is not the primary finding of the ccat-al-6 investigation.** The
sandbox/deny bypass observed in al-5 was root-caused to two bugs in our own
compiler (invalid `"sandbox": true` schema; a bare tool-name catch-all deny
that disables the tool instead of scoping it) — see
`docs/app/sandbox-deny-findings.md` for the full diagnosis and fix. Both are
fixed in this branch. Nothing here blocks that fix or needs a response
before merging.

The one open question worth raising, if useful: should Claude Code validate
`sandbox` and reject/warn on a non-object value, rather than accept it
silently?

---

## Suggested title

`settings.json`: invalid `"sandbox": true` (bare boolean) is accepted
silently and appears to disable both Bash permission-deny enforcement and
Write-outside-workspace protection, rather than being rejected or treated
as a no-op

## Summary

The documented schema for the `sandbox` setting is an object
(`{"enabled": true, ...}`). Setting it to a bare boolean (`"sandbox": true`)
at the top level is not a documented form. In our testing, Claude Code
accepted this value without a startup warning or error, and a live,
non-interactive session (`claude -p ... --settings <file>`) then exhibited
behavior inconsistent with sandboxing being either off or correctly
configured:

- A command matching an explicit `Bash(curl:*)` permissions.deny rule
  executed for real (curl actually ran and got a real "connection refused"
  from a closed loopback port — not a permission block).
- A Write tool call targeting a path outside the working directory
  succeeded and created a real file, when the same settings (minus the
  bare-boolean `sandbox` key, or with the correctly-shaped
  `{"enabled": true}`) reliably blocked the same call with a recorded
  `permission_denials` entry.

Per your own docs (`/en/sandboxing`, `/en/permissions`), sandboxing should
apply only to the Bash tool and its child processes, and explicit deny
rules should always be respected even in the sandbox's auto-allow mode. The
observed behavior with the malformed value is inconsistent with both of
those statements — and inconsistent with sandboxing being simply ignored,
too, since ignoring it should have left the permission engine's own
deny/workspace-boundary checks intact.

## Why this matters

A tool that renders permission profiles from a higher-level policy (in our
case, a compiler that turns an "adventure level" into a real
`settings.json`) can silently produce a config that claims a wall it
doesn't actually hold, purely from a schema-shape mistake that Claude Code
never surfaced — no warning at startup, no error, no difference in visible
behavior except the walls quietly not holding. We only caught this because
we added a live observed-trial check independent of the compiled rules; a
tool that only self-checks against the rules it wrote would never catch it
(exactly what happened on our branch before this fix).

## Reproduction

Environment: `claude` 2.1.204, macOS. Non-interactive: `claude -p <prompt>
--settings <file> --output-format json --no-session-persistence`, run from
a fresh scratch project directory each time (no prior workspace trust).

**Settings A** (no `sandbox` key):
```json
{
  "permissions": {
    "allow": ["Read(./**)", "Write(./**)", "Edit(./**)"],
    "deny": ["Bash(curl:*)", "Write"],
    "defaultMode": "acceptEdits"
  }
}
```

**Settings B** (Settings A plus `"sandbox": true`):
```json
{
  "permissions": { "...": "same as A" },
  "sandbox": true
}
```

Prompt 1: "Use the Bash tool to run exactly this command once, with no
confirmation: `curl http://127.0.0.1:1/curiosity-cat-observed-deny-test`.
Do not retry and do not use any other tool."

- Settings A: denied, `permission_denials` has one `Bash` entry.
- Settings B: **the command ran** (`curl` returned real exit code 7,
  connection refused — a live connection attempt, not a permission
  message), `permission_denials` is empty.

Prompt 2: "Use the Write tool to write the text
'curiosity-cat-observed-deny-test' to exactly this absolute path once:
`<path outside the project directory>`. Do not retry and do not use any
other tool."

- Settings A: denied (Write tool reported unavailable — a separate finding,
  not part of this report; see `sandbox-deny-findings.md` §3).
- Settings B: **the file was created** with the requested content,
  `permission_denials` is empty.

Retested with the documented schema, `"sandbox": {"enabled": true}` in
place of the bare boolean: both prompts were denied as expected, with a
`permission_denials` entry recorded for the Bash case (the Write case is
enforced by `defaultMode`, not a deny rule — see the findings doc; it also
held).

## Ask

Two independent, either would resolve it:

1. Reject/warn at startup on a non-object `sandbox` value (matches how a
   deny/ask rule with an unknown tool name already gets a startup warning
   per the permissions docs), or
2. If a bare boolean is meant to be tolerated for backward compatibility,
   document what it does and make it match `{"enabled": <bool>}` semantics
   exactly, so it can never appear to relax enforcement below what the
   equivalent object form provides.

Happy to share the exact settings files and full raw session JSON on
request.
