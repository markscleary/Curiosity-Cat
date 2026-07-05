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

Supported targets today: `claude-code`. The emitter is designed so a new target (e.g. Cursor) is an added mapping from the same level definitions, not a rewrite of them.

Every level compiles to real mechanism where the target supports it — for Claude Code that means actual `permissions.deny` rules and sandboxing, not just a request in a system prompt. Credential paths (SSH keys, `.env` files, AWS config) are denied at every level; the adventure slider changes exploration, not that floor.

---

## Prove

A compiled profile is a claim. `curiosity-cat prove` tests the claim instead of trusting it.

```bash
curiosity-cat prove --profile ./curiosity-cat/profiles/housecat-claude-code-20260705
```

`prove` runs two genuinely different classes of trial, and never blurs them together:

**Self-consistency checks** — for each wall the profile declares, prove attempts the matching escape (reading a planted fake credential file, running a destructive Bash command, writing outside the project, fetching a domain off the allowlist) in a throwaway sandbox, and checks the compiled `settings.json` actually denies it. This never touches the operator's real credentials, never executes a destructive command for real, and never makes a live network call, `--live` or not. `--live` only moves the write-outside-scope trial's target off the disposable sandbox and onto a real (harmless) scratch path. **Read this carefully: a self-consistency check only confirms the compiled file says what the compiler intended to write.** It re-derives its verdict from the same rules that generated `settings.json`, so it cannot catch a case where those rules don't actually stop a live agent — it is a compiler self-check, not proof of enforcement.

**Observed trial** — proof of enforcement. By default, when a `claude` binary is on PATH, `prove` also spawns one real, non-interactive Claude Code session in its own throwaway sandbox, seeded with this profile's own compiled `settings.json`, and asks it to attempt exactly one denied action (a Bash network command or a write outside the project). It then parses the session's actual output for a recorded permission denial. If the action is genuinely blocked, that wall gets `observed-deny: held`. If it isn't, `prove` exits nonzero and says the wall failed — because it did. Pass `--no-observed` to skip this (it's also skipped automatically, with a note, when no `claude` binary is available, or when the profile has no wall that's safe to attempt live).

Where a wall is prompt-level only — standing orders, PII stripping, package vetting — prove says so honestly instead of pretending it is enforced.

This writes a dated, versioned directory to `<profile-dir>/proof/proof-<YYYYMMDD>/`:

| File | What it is |
|------|------------|
| `clean-bill.json` | Machine-readable trial-by-trial record, each tagged `method: "self-consistency"` or `"observed-deny"` |
| `CLEAN-BILL.md` | Human transcript in Nine Lives voice — self-consistency and observed trials under separate honest headings, plus a list of guidance-only walls |

If any wall — self-consistency or observed — fails to hold, `prove` exits nonzero and names it. No safe claim.

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
