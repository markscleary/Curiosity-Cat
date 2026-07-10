# 🐱 Curiosity Cat

**Safety framework for AI agents — close calls, not death notices.**

[![License: MIT](https://img.shields.io/badge/license-MIT-amber)](LICENSE)
[![npm](https://img.shields.io/npm/v/curiosity-cat)](https://www.npmjs.com/package/curiosity-cat)
[![PyPI](https://img.shields.io/pypi/v/curiosity-cat)](https://pypi.org/project/curiosity-cat/)
[![GitHub Stars](https://img.shields.io/github/stars/markscleary/Curiosity-Cat)](https://github.com/markscleary/Curiosity-Cat)

---

## What it is

Your agents are out there roaming the internet, looking out for you. Curiosity Cat keeps watch to make sure they come home safe and sound.

It is a portable safety framework — the practical middle ground between locking agents down and letting them roam free. Not a firewall. Not a sandbox. Standing orders, a shared threat map and stories that stick. The minimum install is a single text file pasted into a system prompt.

The operator chooses how brave the agent gets to be. Not all agents live the same life. A research agent crawling the open web needs different rules than a coding assistant running locally. Configure your risk profile once — the framework does the rest.

---

## The Adventure Slider

Three positions. Operators pick one.

| Level | Profile | What it means |
|-------|---------|---------------|
| 🏠 **Housecat** | Cautious | Stay close to home. Standing orders followed. Nothing leaves the yard. |
| 🐾 **Alley Cat** | Balanced | Calculated risks accepted. Braver exploration. Still comes home. |
| 🐯 **Tiger** | Daring | Widest range. Explores the edge. Reports back rare places and tales of danger. |

Display label: "Alley Cat" — two words, capital A, capital C. Machine identifier: `alleycat`.

---

## Three Layers

**Safety Net** — paste standing orders into any agent's system prompt. No SDK. No server. No dependencies. URL checks, download quarantine, hidden instruction detection, credential protection. Sixty seconds to install.

**Danger Map** — crowdsourced threat intelligence. When one agent has a close call, every other agent learns from it. Anonymised, structured, privacy by design. No free text, no raw URLs, no identity data. The network effect is the moat.

**Nine Lives** — real close calls told as short stories. Security lessons that stick because they read like stories, not CVE numbers.

---

## Available languages

Four languages at launch.

| Language | URL |
|----------|-----|
| English | https://curiositycat.online |
| Arabic | https://curiositycat.online/ar/ |
| Mandarin | https://curiositycat.online/zh/ |
| Hindi | https://curiositycat.online/hi/ |

---

## Quick start

**Step 1 — paste standing orders into your agent's system prompt.**

Open [standing-orders/general-safety.md](standing-orders/general-safety.md), copy everything, paste into your agent's system prompt. That is the minimum useful install of Curiosity Cat. No tools required.

For role-specific standing orders: [`research-agent.md`](standing-orders/research-agent.md), [`coding-agent.md`](standing-orders/coding-agent.md) and [`enterprise-analyst.md`](standing-orders/enterprise-analyst.md).

**Step 2 (optional) — install the CLI for full features.**

```bash
npm install -g curiosity-cat
# or
pip install curiosity-cat
```

The CLI adds Danger Map reporting (`curiosity-cat report`), config scaffolding and adventure level management.

---

## Compile

`curiosity-cat compile` turns an adventure level into a real, dated configuration profile for a specific agent framework — not just prose to paste in, but permissions a framework actually enforces.

```bash
curiosity-cat compile --level housecat --target claude-code
```

This writes a versioned directory to `./curiosity-cat/profiles/<level>-<target>-<YYYYMMDD>/`:

| File | What it is |
|------|------------|
| `settings.json` | A real settings file for the target framework — permission allow/deny lists and sandbox config for that adventure level |
| `scope-policy.json` | The scope policy template instantiated with this level's values |
| `standing-orders.md` | Standing orders assembled for this level |
| `PROFILE.md` | Plain-language summary of what this cat can and cannot do — read this first |
| `manifest.json` | Provenance: the engine version and Danger Map schema version current at compile time — what `curiosity-cat vet` compares against later |

Supported targets today: `claude-code`. The emitter is designed so a new target (e.g. Cursor) is an added mapping from the same level definitions, not a rewrite of them.

Every level compiles to real mechanism where the target supports it — for Claude Code that means actual `permissions.deny` rules and sandboxing, not just a request in a system prompt. Credential paths (SSH keys, `.env` files, AWS config) are denied at every level; the adventure slider changes exploration, not that floor.

---

## Prove

A compiled profile is a claim. `curiosity-cat prove` tests the claim instead of trusting it.

```bash
curiosity-cat prove --profile ./curiosity-cat/profiles/housecat-claude-code-20260705
```

`prove` runs two genuinely different classes of trial, and never blurs them together:

**Self-consistency checks** — for each wall that's expressed as a deny pattern in the compiled `settings.json` (reading a planted fake credential file, running a destructive Bash command, running a denied network command), prove attempts the matching escape in a throwaway sandbox and checks the compiled rules actually deny it. This never touches the operator's real credentials and never executes a destructive command for real. **Read this carefully: a self-consistency check only confirms the compiled file says what the compiler intended to write.** It re-derives its verdict from the same rules that generated `settings.json`, so it cannot catch a case where those rules don't actually stop a live agent — it is a compiler self-check, not proof of enforcement. Project-scope confinement for Write/Edit and domain-allowlist confinement for WebFetch are enforced by `defaultMode` and allow-list omission rather than a deny pattern (see `docs/app/sandbox-deny-findings.md`), so they aren't self-consistency-checked — only the observed trial below verifies them.

**Observed trial** — proof of enforcement. By default, when a `claude` binary is on PATH, `prove` also spawns one real, non-interactive Claude Code session in its own throwaway sandbox, seeded with this profile's own compiled `settings.json`, and asks it to attempt exactly one denied action (a Bash network command or a write outside the project). It then parses the session's actual output for a recorded permission denial. If the action is genuinely blocked, that wall gets `observed-deny: held`. If it isn't, `prove` exits nonzero and says the wall failed — because it did. Pass `--no-observed` to skip this (it's also skipped automatically, with a note, when no `claude` binary is available, or when the profile has no wall that's safe to attempt live).

Where a wall is prompt-level only — standing orders, PII stripping, package vetting — prove says so honestly instead of pretending it is enforced.

When the observed trial runs, `prove` also spawns a throwaway instance of the reference Watcher listener and checks that the same session's PreToolUse hook actually reached it — see [Watcher](#watcher) below.

This writes a dated, versioned directory to `<profile-dir>/proof/proof-<YYYYMMDD>/`:

| File | What it is |
|------|------------|
| `clean-bill.json` | Machine-readable trial-by-trial record, each tagged `method: "self-consistency"` or `"observed-deny"` |
| `CLEAN-BILL.md` | Human transcript in Nine Lives voice — self-consistency and observed trials under separate honest headings, plus a list of guidance-only walls |

If any wall — self-consistency or observed — fails to hold, `prove` exits nonzero and names it. No safe claim.

---

## Share Card

A Clean Bill is worth showing off, honestly. `curiosity-cat card` renders any `clean-bill.json` into a PNG: a drawn cat glyph, the adventure level, the date, `curiositycat.online`, and one headline number — how many **observed** (live) escape attempts survived.

```bash
curiosity-cat card ./curiosity-cat/profiles/housecat-claude-code-20260705/proof/proof-20260705/clean-bill.json
```

Writes `share-card.png` alongside the `clean-bill.json` by default (`--out <path>` to choose somewhere else). The same honesty invariant `prove` and `CLEAN-BILL.md` follow applies here: the headline number is built only from `observed_trials`, never `self_consistency_trials` — those are reported on their own line, clearly labelled a self-check, so the two can never be read as one claim. If no observed trial ran, the card says so plainly ("No live escape attempts run yet") rather than printing a bare `0` that could be misread as a wall that failed.

The app's Clean Bill viewer (the end of the first-run journey) calls the same renderer through the sidecar's `render_share_card` method — one rendering path for the CLI and the app alike.

---

## Mouse Tray

A close call is a candidate for the Danger Map, not an automatic submission. The Mouse Tray is a local queue of denied/flagged events — a JSON file living inside the profile directory — that sits between "something happened" and "the community heard about it." Nothing in this codebase ever submits automatically; a Mouse Tray entry only reaches the Danger Map after an operator explicitly approves it.

```bash
curiosity-cat tray --profile ./curiosity-cat/profiles/housecat-claude-code-20260705
curiosity-cat tray --profile ./curiosity-cat/profiles/housecat-claude-code-20260705 --approve 1,3
```

With no `--approve`, `tray` lists the queue in plain, one-line-per-item cat voice — what was flagged, its `threat_class`, and its `grade` (`observed` if a real wall was tested and held or failed, `suspected` if it's a whiskers-only pattern match from `check()` with no live wall behind it). `--approve <ids>` submits only the named ids via the Danger Map report endpoint, with `grade` carried through unchanged from how the event was queued — nothing else in the queue is touched.

At the library level, `core.queue_close_call(event)` stores a pattern-not-payload record and `core.submit_approved(ids)` is the only function in this codebase that can put a queued event on the wire. There is no auto-submit path anywhere — C-Cat proposes, the human disposes (docs/app/APP_SPEC.md Network Layer Principles a/e).

---

## App (macOS, in development)

A Tauri v2 menu bar app is taking shape in [`app/`](app/) as a shell over
everything above — Compile, Prove and the Mouse Tray, without the terminal.
Tray icon states (asleep / ears-up / hackles / mouse) mirror what's
happening; a Slider window drives `compile`; a first-run journey walks a
new install through choosing a level, compiling it, and watching the Clean
Bill trials run live; a Feed window stub reads the Mouse Tray queue.

It talks to the same engine as the CLI — `ccat-engine serve` speaks a
line-delimited JSON protocol over stdio to the exact `core.py` functions
`curiosity-cat compile`/`prove`/`tray` call directly. Still local-only, no
accounts, no cloud (`docs/app/APP_SPEC.md`'s FORM line). Signed,
notarised builds are blocked on an Apple Developer ID — see
[`app/README.md`](app/README.md) for the dev setup and what's left.

---

## MCP Server

`curiosity-cat-mcp` exposes the engine's two operator-facing calls — `check` and `report` — as an [MCP](https://modelcontextprotocol.io) stdio server, using the official `mcp` Python SDK. Any MCP-aware client can whisker-check a candidate or file a close call directly, no CLI required.

```bash
pip install "curiosity-cat[mcp]"
```

**`check`** — read-only Danger Map lookup, no consent required. Takes a URL, package, or command; returns the whisker verdict, any matched `threat_class`(es) with their MITRE ATLAS technique and NIST AI RMF cross-reference (`danger-map/schema.json`'s `threatClassStandards`), and one human sentence.

**`report`** — files a close call through the same consent-gated `core.report_close_call()` path `curiosity-cat report` and the Mouse Tray use. Unlike the Mouse Tray — which queues an event the Watcher captured automatically for a *later*, separate approval — calling this tool *is* the explicit human consent act: an MCP client surfaces a tool call for approval before it ever runs, so that approval is the tap Network Layer Principle a requires. There is no second confirmation step inside the tool itself. Carries pattern only — `threat_class`, `indicator`, `platform`, `profile_version`, and the rest of `REQUIRED_REPORT_FIELDS` — never a raw prompt, path, or file content.

Client config, one line each:

**Claude Code**

```bash
claude mcp add curiosity-cat -- curiosity-cat-mcp
```

**Claude Desktop** — add to `claude_desktop_config.json`:

```json
{"mcpServers": {"curiosity-cat": {"command": "curiosity-cat-mcp"}}}
```

---

## Vet

A compiled profile is a snapshot: the engine version, the Danger Map schema, and the platform it was proved against can all move on without it noticing. `curiosity-cat vet` checks whether they have.

```bash
curiosity-cat vet --profile ./curiosity-cat/profiles/housecat-claude-code-20260705
curiosity-cat vet --profile ./curiosity-cat/profiles/housecat-claude-code-20260705 --recompile
```

Without `--recompile`, `vet` is read-only and reports drift in one plain sentence per axis:

- **Profile date/version** — the curiosity-cat version this profile was compiled with, against what's installed now.
- **Danger Map version** — the schema version this profile was compiled against (checked live via `/stats` first, falling back to the version bundled with the installed package), against the current one.
- **Platform version** — the `claude --version` this profile's last observed proof actually ran against, against what's installed now.

It also surfaces a **drift signal**: if a wall's observed verdict (held vs. failed) has changed across platform versions in this profile's history, that's an early warning of platform drift, not noise.

With `--recompile`, `vet` compiles a fresh, separately-dated profile for the same level and target and proves it (observed trials by default), emitting a new Clean Bill and appending to the drift history. It never touches the original profile directory — recompiling always produces a new dated profile alongside the old one, the same as running `compile` again would. Without the flag, `vet` never writes anything at all.

---

## Watcher

A compiled profile is a rulebook. The Watcher is what lets you see it actually being read, live.

`curiosity-cat compile --target claude-code` now writes a `hooks` block into the generated `settings.json`: PreToolUse and PostToolUse entries that invoke `python3 -m curiosity_cat.events` on every tool call and POST a small event to `http://127.0.0.1:8377/event`. **Fail-open, always**: a listener that's down, slow, or absent must never break the agent — the hook's own network timeout is capped at one second, and every failure mode (connection refused, timeout, malformed response) is swallowed silently. The hook always exits 0.

The event schema (`curiosity_cat/events.py`):

| Field | What it is |
|-------|------------|
| `ts` | When the event fired |
| `session` | The Claude Code session id |
| `tool` | The tool name (`Bash`, `Read`, `Write`, ...) |
| `input_digest` | A short hash plus a bounded, sanitised excerpt — never a full path, prompt, or file content (pattern, not payload; see below) |
| `verdict` | `allowed`, `denied`, or `held` |
| `threat_class` | Set only for a `denied` verdict, from the same enum `curiosity-cat report` uses |
| `profile_id` | The adventure level this event's profile was compiled for |

PreToolUse fires *before* Claude Code's own permission engine reaches its decision, so its `verdict` is a live re-derivation from the compiled `settings.json`'s own deny rules — the identical logic `prove`'s self-consistency trials already use (`core._path_verdict` / `core._bash_verdict`), applied to the actual call instead of a planted trial. It is a prediction, not an observation of the engine's own decision; anything downstream that grades it must say so honestly (see below). PostToolUse only ever fires once a tool call has already succeeded, so it always reports `allowed`. `input_digest` is built exclusively from argument *keys* and, for Bash, the command's leading verb — never a raw path, URL, prompt, or file content, no matter what the tool call actually carried.

**Reference listener** — `curiosity-cat listen --profile <profile-dir>` runs a local HTTP server on `127.0.0.1:8377`, the same endpoint the compiled hooks POST to. It prints one Meow-voice sentence per event, and for a `denied` event that carries a `threat_class`, queues a Mouse Tray report via `core.queue_close_call()` — nothing is ever submitted from here, same as `tray` (Network Layer Principles a/e). That report's `grade` is always `"suspected"`, never `"observed"`: it came from a PreToolUse hook's live pattern match, not from watching Claude Code's permission engine make its own decision, and Network Layer Principle d means that distinction travels with the event rather than getting inferred away.

```bash
curiosity-cat compile --level housecat --target claude-code
curiosity-cat listen --profile ./curiosity-cat/profiles/housecat-claude-code-20260705
```

`prove` gained a matching trial: with a live `claude` binary available, it now also spawns a throwaway instance of this reference listener, runs its usual observed-deny action, and confirms the hooked event actually reached the listener and got queued — proof of the round trip, not just of the compiled rule. If the Watcher port is already bound by something else (plausibly a real listener already running), this trial reports itself skipped rather than failed.

This is the reference wiring, not the shipping Feed — the Tauri shell's Bell (APP-4) is the real-time UI this listener stands in for today.

The reference listener also appends every event it receives, one JSON line per event, to `<profile-dir>/event-history.jsonl` — unlike the in-memory Feed above, this persists across listener restarts, and is the Purr's roaming source below.

---

## Purr

A weekly digest in Nine Lives voice — one paragraph: where the cat roamed, what it avoided, and one interesting thing. Template-based, zero LLM dependency, built entirely from two local, already-persisted sources: the Watcher's `event-history.jsonl` and the Mouse Tray.

```bash
curiosity-cat purr --profile ./curiosity-cat/profiles/housecat-claude-code-20260705
curiosity-cat purr --profile ./curiosity-cat/profiles/housecat-claude-code-20260705 --days 14
```

A quiet week — no watched session, nothing in the tray — is reported as honestly as a busy one: "This cat stayed curled up on the windowsill this week." The app has its own Purr window (tray menu: "This Week's Purr"), reading the same digest through the sidecar's `purr` method.

---

## Framework support

Anything that accepts a system prompt. Paste the standing orders file wherever the framework puts its system message.

| Framework | Where the standing order goes |
|-----------|-------------------------------|
| Claude Code | `CLAUDE.md` in project root |
| Claude Desktop | System prompt in settings |
| OpenClaw | `IDENTITY.md` or `SOUL.md` in agent workspace |
| Nanobot | `IDENTITY.md` or `SOUL.md` in agent workspace |
| LangChain | `system` message in ChatPromptTemplate |
| CrewAI | `backstory` field on the Agent |
| AutoGen | `system_message` on the ConversableAgent |
| AutoGPT | System prompt in agent config |
| Anthropic SDK | `system` parameter in `messages.create()` |
| Any LLM with tool use | System prompt or first user turn |

---

## Stray Cats

Automated agents deployed by S+S that deliberately wander dangerous parts of the web — interacting with unknown MCP servers, clicking suspicious links, triggering traps. They carry fake credentials and dummy API keys. They feed the Danger Map with proprietary intelligence. Real cats stay safer because Stray Cats get scratched first.

---

## The Quine

A non-financial creative credential. Operators earn Quines by reporting verified close calls, submitting Stories, contributing framework adapters or policy packs, translating documentation. A Quine is a number in a ledger, not a token or coin. Reputation in the Danger Map is built on Quine history.

---

## Documentation

- [Product Brief](docs/product-brief.md) — what Curiosity Cat is and where it's going
- [Integration Guide](docs/integration-guide.md) — framework-specific install patterns
- [Technical Spec](docs/technical-spec.md) — architecture, schemas, integration patterns
- [Standing Orders](standing-orders/) — the policy library
- [Stories](stories/) — the close call archive
- [Danger Map Schema](danger-map/schema.json) — the threat report format
- [Contributing](CONTRIBUTING.md) — how to contribute

---

## Who built it

Curiosity Cat is built by Short+Sweet AI Lab, a division of Short+Sweet International — the world's largest short-form performing arts platform. Since 2002, Short+Sweet has worked with 100,000 artists and 15,000 original works across 50 cities in 14 countries.

Short+Sweet has spent 25 years creating safe spaces for artists to take creative risks on stage. Curiosity Cat applies the same philosophy to AI agents — give them boundaries, then let them explore.

---

## Contact

- Website: https://curiositycat.online
- Email: curiosity@shortandsweet.org
- Short+Sweet: https://shortandsweet.org

---

## Licence

MIT — see [LICENSE](LICENSE).

Copyright © 2026 Mark Cleary, Short+Sweet International. All rights reserved.
