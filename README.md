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
| 🏠 **Housecat** | Cautious | Stay close to home. Standing orders enforced. Nothing leaves the yard. |
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

Five languages at launch.

| Language | URL |
|----------|-----|
| English | https://curiositycat.online |
| Arabic | https://curiositycat.online/ar/ |
| Mandarin | https://curiositycat.online/zh/ |
| Hindi | https://curiositycat.online/hi/ |
| Tamil | https://curiositycat.online/ta/ |

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
