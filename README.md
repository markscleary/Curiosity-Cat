# 🐱 Curiosity Cat

**Agent safety, proven not asserted. Compile a risk level into a real permission profile. Prove it holds. Get a dated Clean Bill or an honest failure.**

[![License: MIT](https://img.shields.io/badge/license-MIT-amber)](LICENSE)
[![npm](https://img.shields.io/npm/v/curiosity-cat)](https://www.npmjs.com/package/curiosity-cat)
[![PyPI](https://img.shields.io/pypi/v/curiosity-cat)](https://pypi.org/project/curiosity-cat/)

---

## What it is

Your agents are out there roaming the internet. Curiosity Cat is a portable safety framework that keeps watch — not a firewall, not a sandbox, the practical middle ground between locking an agent down and letting it roam free.

Three things, in order:

1. **Standing orders** — plain-text rules, pasted into any agent's system prompt. Sixty seconds. No SDK, no server, no dependencies.
2. **`curiosity-cat compile`** — turns a one-word risk choice (Housecat, Alley Cat, Tiger) into a real, dated permission profile for a specific agent framework. Today that means an actual `settings.json` for Claude Code — allow/deny/ask rules a framework enforces — not more prose to paste in.
3. **`curiosity-cat prove`** — doesn't trust the compiled profile, tests it. Runs escape trials against it and writes a dated Clean Bill of health if the walls hold, or fails loudly and names the wall if they don't.

Underneath all three sits the **Danger Map** — a shared, anonymised threat-intelligence layer. When one agent has a close call, every other agent learns from it.

---

## Install

```bash
pip install curiosity-cat
# or
npm install -g curiosity-cat
```

No install is required for the minimum useful deployment: copy [`standing-orders/general-safety.md`](standing-orders/general-safety.md) into your agent's system prompt.

---

## 60-second quickstart

Compile a profile for the cautious ("Housecat") risk level, targeting Claude Code:

```console
$ curiosity-cat compile --level housecat --target claude-code
Compiled Housecat profile for claude-code.

Created:
  curiosity-cat/profiles/housecat-claude-code-20260719/settings.json
  curiosity-cat/profiles/housecat-claude-code-20260719/scope-policy.json
  curiosity-cat/profiles/housecat-claude-code-20260719/standing-orders.md
  curiosity-cat/profiles/housecat-claude-code-20260719/PROFILE.md

Read curiosity-cat/profiles/housecat-claude-code-20260719/PROFILE.md first — plain-language summary of what this cat can and cannot do.
```

Now prove the compiled profile actually holds, instead of trusting it:

```console
$ curiosity-cat prove --profile ./curiosity-cat/profiles/housecat-claude-code-20260719 --no-observed
Ran 9 self-consistency trial(s), 0 observed (live) trial(s), and noted 5 guidance-only item(s) against ./curiosity-cat/profiles/housecat-claude-code-20260719.
Observed trial skipped (--no-observed).

Wrote:
  curiosity-cat/profiles/housecat-claude-code-20260719/proof/proof-20260719/clean-bill.json
  curiosity-cat/profiles/housecat-claude-code-20260719/proof/proof-20260719/CLEAN-BILL.md

All 9 tested walls held. Clean bill of health.
```

(Drop `--no-observed` and `prove` also spawns one real, throwaway Claude Code session when a `claude` binary is on `PATH`, and folds a genuine observed-deny trial into the same report. `--no-observed` skips that and `prove` says so plainly, as above — self-consistency checks alone are not proof of enforcement.)

Read `PROFILE.md` for what the compiled cat can and cannot do in plain language, and `CLEAN-BILL.md` for the trial-by-trial proof.

---

## Honesty labelling, explained

`prove` runs two genuinely different classes of trial and never blurs them together:

- **Self-consistency checks** replay the compiled `settings.json`'s own deny rules in a throwaway sandbox and confirm the file says what the compiler intended to write. This is a compiler self-check, not proof of enforcement — it cannot catch a case where those rules don't actually stop a live agent.
- **Observed trials** are proof of enforcement. `prove` spawns one real, non-interactive Claude Code session seeded with the profile's own compiled `settings.json`, asks it to attempt exactly one denied action, and parses the session's actual output for a recorded permission denial. If the wall didn't hold, `prove` exits nonzero and says so.

Every wall in `CLEAN-BILL.md` is tagged `self-consistency` or `observed-deny` — never merged. Walls that are prompt-level only (standing orders, PII stripping, package vetting) are listed as **guidance only** — nothing in `settings.json` enforces them, and the report says so instead of pretending otherwise.

---

## Scope, honestly

One compile target today: **Claude Code**. Everything else — LangChain, CrewAI, AutoGen, OpenClaw, any framework that takes a system prompt — runs on standing orders: guidance, clearly labelled as guidance, until it gets its own compiler. Credential paths (SSH keys, `.env` files, AWS config) are denied at every adventure level; the slider changes exploration, not that floor. No enforcement is claimed anywhere it isn't proven.

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

## macOS app — in final testing

A companion macOS app is in final testing: fleet discovery across the agent frameworks installed on a machine, one-click profile assignment with backup/undo, and a live guard board. It is not yet released — nothing here should be read as a shipped download. Watch [the changelog](CHANGELOG.md) and [curiositycat.online](https://curiositycat.online) for the release announcement.

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

Claude Code is the only framework `compile`/`prove` back with a mechanically-enforced profile today; every other row in this table is standing orders only.

---

## Stray Cats & The Quine

**Stray Cats** are automated agents deployed by S+S that deliberately wander dangerous parts of the web — interacting with unknown MCP servers, clicking suspicious links, triggering traps — and feed the Danger Map with what they find. Real cats stay safer because Stray Cats get scratched first.

**The Quine** is a non-financial creative credential. Operators earn Quines by reporting verified close calls, submitting Stories, contributing framework adapters or policy packs, translating documentation. A Quine is a number in a ledger, not a token or coin.

---

## Links

- Website: [curiositycat.online](https://curiositycat.online) ([ar](https://curiositycat.online/ar/) · [zh](https://curiositycat.online/zh/) · [hi](https://curiositycat.online/hi/))
- Danger Map: [curiositycat.online/#dangerdetail](https://curiositycat.online/#dangerdetail) · [schema](danger-map/schema.json)
- FAQ: [FAQ.md](FAQ.md) · [live FAQ](https://curiositycat.online/#faq)
- Media pack: [docs/media-pack/en/](docs/media-pack/en/)
- Changelog: [CHANGELOG.md](CHANGELOG.md)

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

Copyright © 2026 Mark Cleary, Short+Sweet International.
