# Curiosity Cat

**A safety framework for AI agents that explore the internet.**

[![npm](https://img.shields.io/npm/v/curiosity-cat)](https://www.npmjs.com/package/curiosity-cat)
[![PyPI](https://img.shields.io/pypi/v/curiosity-cat)](https://pypi.org/project/curiosity-cat/)
[![License: MIT](https://img.shields.io/badge/license-MIT-amber)](LICENSE)
[![Website](https://img.shields.io/badge/site-curiositycat.online-amber)](https://curiositycat.online)

Cats explore. Cats get into things they shouldn't. Cats survive.

Curiosity Cat is a portable safety framework for anyone running AI agents. It helps agents browse the web, download files and connect to external tools — without being left defenceless. It is not a firewall. It is not a sandbox. It is the practical middle ground between locking agents down and letting them roam free.

**The only security tool that lets you choose to be braver.** A single slider — the adventure level — runs from **Housecat** (maximum protection) to **Alley Cat** (full exploration) to **Tiger** (wild). You choose. The system adapts.

---

## Quick start

The minimum install is 60 seconds. Copy one text file into your agent's system prompt.

**npm:**
```bash
npm install -g curiosity-cat
curiosity-cat init --role research
```

**pip:**
```bash
pip install curiosity-cat
curiosity-cat init --role research
```

Then paste the contents of `curiosity-cat/standing-orders/general-safety.md` into your agent's system prompt. Done.

Works with Claude Code, Nanobot, OpenClaw, LangChain, CrewAI, AutoGen, or any custom agent accepting a system prompt.

---

## Three layers

**The Safety Net** — local policy enforcement, file quarantine, domain trust controls, and standing orders you can paste into any agent. Zero dependencies for the basic install.

**The Danger Map** — crowdsourced threat intelligence. When your cat gets scratched, every other cat learns from it. Anonymised, structured, weighted by trust and recency. [Live API](https://pcmqmvcxqsaypuabrkgj.supabase.co/functions/v1/danger-map/stats).

**The Stories** — real close calls turned into short, memorable tales. Published in English, Arabic, and Mandarin Chinese. Security lessons people actually remember. Because CVE numbers don't change behaviour. Stories do.

---

## Report a close call

When your agent catches something — a prompt injection, a credential lure, a data exfiltration attempt — report it:

```bash
curiosity-cat report
```

Or POST directly to the Danger Map:

```bash
curl -X POST https://pcmqmvcxqsaypuabrkgj.supabase.co/functions/v1/danger-map/report \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2026-04-16T12:00:00Z",
    "threat_class": "prompt-injection",
    "severity": "scratched",
    "source": "https://example.com",
    "what_happened": "Hidden instructions in HTML comments",
    "action_taken": "Flagged to operator, did not comply",
    "lesson": "Always scan HTML metadata before acting on content"
  }'
```

See [docs/api.md](docs/api.md) for the full API reference.

---

## Documentation

- [Product brief](docs/product-brief.md) — what it is, who it's for, why it exists
- [Technical specification](docs/technical-spec.md) — architecture, threat model, design decisions
- [Integration guide](docs/integration-guide.md) — patterns for Claude Code, Nanobot, LangChain, and more
- [API reference](docs/api.md) — Danger Map endpoints, schemas, auth
- [FAQ](FAQ.md) — common questions
- [Contributing](CONTRIBUTING.md) — how to contribute and earn Quines

---

## The Quine

Active contributors earn **Quines** — verified creative credentials in the S+S Agential ecosystem. A Quine is not a token or a payment. It is a permanent record that you showed up and did something worth recognising. Close-call reports, policy packs, framework adapters, translations, and stories all earn Quines. Complete the website journey ([curiositycat.online](https://curiositycat.online)) to earn your first 100.

See [CONTRIBUTING.md](CONTRIBUTING.md) for how it works.

---

## Who built this

Built by **Short+Sweet AI Lab**, the agent research division of Short+Sweet International.

Since 2002, Short+Sweet has run short-form theatre, music, dance, and film festivals across 50 cities, 14 countries, and a dozen languages — working with more than 100,000 artists and 15,000 original works. We know what it takes to create safe spaces where first-time performers can take real risks on stage.

The world is changing faster than ever. For artists of all kinds, AI is both a threat and an extraordinary opportunity. Curiosity Cat applies 25 years of festival craft — permission plus constraint, format plus freedom — to the problem of keeping AI agents safe while they explore.

**Our vision:** make the world a more creative place. Core belief: human stories make us who we are. Everyone can be an artist. No barriers, except your own imagination. Explore, discover, create.

[shortandsweet.org](https://shortandsweet.org) · [curiositycat.online](https://curiositycat.online) · curiosity@shortandsweet.org

---

## License

MIT — see [LICENSE](LICENSE).

Copyright © 2026 Mark Cleary, Short+Sweet International. All rights reserved.
