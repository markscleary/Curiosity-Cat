# Frequently Asked Questions

## What is Curiosity Cat?

A safety framework for AI agents that explore the internet. It helps your agents inspect, filter, quarantine and report risky external inputs before those inputs are trusted, stored or acted on. The minimum install is copying a text file into your agent's system prompt. That takes sixty seconds.

## How does it work?

Three layers. The Safety Net is a set of standing orders — plain text rules your agent follows. The Danger Map is shared threat intelligence — when one agent has a close call, every other agent learns from it. Nine Lives are the stories — real close calls told plainly so people remember the lessons.

## What frameworks does it support?

Anything that accepts a system prompt. Claude Code, Nanobot, OpenClaw, LangChain, CrewAI, AutoGen, or anything custom. The standing orders are plain text. If your agent can read instructions, it can use Curiosity Cat.

## What does it cost?

The core framework is free and open source. Personal use, open-source projects and agent framework providers pay nothing. Team and enterprise tiers with private Danger Map instances, custom policy packs and auditable decision trails are planned.

## What does it actually protect against?

Prompt injections hidden in web pages, HTML comments, CSS-hidden text and document metadata. Malicious downloads disguised as legitimate packages. Credential phishing through fake authentication pages. Data exfiltration through search queries that leak internal information. Permission escalation where agents use tools beyond their defined scope. Deceptive redirect chains. Memory poisoning through corrupted external content.

## Is this just a system prompt?

The minimum install is a system prompt addition — and that alone provides meaningful protection. The full framework includes scope policies, file quarantine, domain trust controls, policy packs for different agent types and the shared Danger Map intelligence layer.

## Does it slow my agent down?

No. The standing orders are read once when the agent starts. They add no latency to operations. The quarantine and reporting happen only when something suspicious is detected — which is exactly when you want your agent to slow down.

## How is this different from guardrails or content filters?

Guardrails filter what an agent says. Curiosity Cat protects what an agent does — where it goes, what it downloads, what it trusts, what it reports. It is an operational safety layer, not a content moderation tool.

## Who built this?

Short+Sweet International — a performing arts organisation that has spent 25 years creating safe spaces for creative risk-taking across 15 countries. The same philosophy applies: give people boundaries, then let them explore.

## Why is a theatre company building agent security?

Because the problem is the same. For 25 years S+S has helped first-time artists take risks on stage and survive the experience. The people deploying agents right now are in the same position — excited, exposed and learning as they go. They need a system that helps them survive the exploration, not one that stops them from exploring.

## What is The Quine?

A non-financial creative credential. Not a token, not a coin, not a payment. A verified record of contribution — a number in a ledger that proves you showed up and did something worth recognising. Operators earn Quines by reporting verified close calls, submitting stories, contributing framework adapters and translating documentation.

## What are Stray Cats?

Automated exploration agents deployed by S+S that deliberately wander dangerous parts of the web, interact with unknown MCP servers, click suspicious links and trigger traps. They carry fake credentials and dummy API keys. They are designed to get scratched so that real agents do not have to. Their findings feed the Danger Map.

## What languages does it support?

English, Arabic and Mandarin Chinese from launch. No agent security product currently exists in Arabic. Additional languages are added as the community contributes translations.

## Can I contribute?

Yes. Framework adapters, policy packs, translations, stories and threat reports are all welcome. See CONTRIBUTING.md for details. Contributions earn Quines.

## Is my data safe?

The Danger Map never collects user identity, personal information, agent configurations, API keys, credentials, IP addresses or the content of the work being done. Reports are structured, sanitised and anonymous by design. Operators can choose full reporting, domain-only reporting or local-only mode where no data leaves their system.

## What if I just want to try it without signing up for anything?

Copy the contents of standing-orders/general-safety.md into your agent's system prompt. That is the whole install. No account, no registration, no API key. Your agent is protected.
