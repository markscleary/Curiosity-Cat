# Curiosity Cat — Product Brief

*Curiosity Cat v0.2. Proven, not asserted.*

## What it is

Curiosity Cat is an open-source safety tool for people who run AI agents without a security team. Enterprise agent platforms ship with security teams attached. The independent operator running agents from a home machine or a small studio has, until now, had guidance documents and good luck.

The product does three things, in order. **Compile** turns a plain-language risk choice into a real, hardened permission profile for the agent. **Prove** attacks that profile with escape trials to see whether it actually holds. **Clean Bill** writes down what happened — a dated report that can fail, and says so when it does.

## Who it's for

Anyone running agents that touch external content without a dedicated security function behind them: solo developers, small studios, open-source maintainers, and teams running an agent fleet from a single machine. Curiosity Cat is built by operators in exactly that position — Short+Sweet runs its own agent fleet from a Mac Mini and kept hitting the same problem everyone else does.

## Compile, prove, Clean Bill

The operator chooses one of three risk levels — Housecat, Alley Cat or Tiger — and runs:

```
curiosity-cat compile --level housecat --target claude-code
```

That is not advice to paste into a system prompt. It writes a real settings file: allow, deny and ask rules a framework actually enforces. Housecat confines reads and writes to the project and fetches from an explicit domain allowlist; Tiger widens the range. Credential paths — SSH keys, `.env` files, cloud config — are denied at every level. The slider changes how far the agent explores, not that floor.

A compiled profile is a claim, not a fact, so `curiosity-cat prove` tests it. Two genuinely different kinds of trial run, and the report never blurs them together. **Self-consistency checks** replay the compiled rules against themselves in a throwaway sandbox — they confirm the settings file says what the compiler intended. **Observed-deny trials** go further: where it's safe to do so, `prove` spawns a real, non-interactive Claude Code session inside the compiled profile, asks it to attempt exactly one denied action, and records whether it was actually stopped. Only the observed trial proves a running agent was stopped; the self-consistency check proves the file is well-formed. Every line of every report says which kind it is.

The result lands in `CLEAN-BILL.md` — one sentence per trial, dated, honest about guidance-only walls that aren't enforced by mechanism yet. If any wall fails, `prove` exits nonzero and names it.

## The cat's first escape

The law — proven, not asserted — isn't a slogan chosen in advance. It came from a bug. Early in development, the proof layer's checks were all self-consistency: rules replayed against themselves, always agreeing with themselves. Once observed-deny trials were built and run for real, the first live trial found a way out. A malformed `sandbox` setting in the compiled profile was quietly bypassing the deny rules — the settings file looked correct, every self-consistency check passed, and a live agent session walked straight through the wall anyway. The bug was fixed before release. The lesson became the product's law: an assertion-only tool would have shipped that hole, and the only reason Curiosity Cat caught it was that it was built to attack its own claims instead of trusting them.

## Honest scope

One compile target ships today: Claude Code. Every other agent framework — OpenClaw, Nanobot, LangChain, CrewAI, AutoGen, anything that accepts a system prompt — runs on Curiosity Cat's standing orders: plain-text briefing language, labelled clearly as guidance, not enforcement, until each target earns its own compiler. Curiosity Cat does not claim to make any agent immune to deception, and it does not replace sandboxing, network controls or secret management. It adds a practical, honestly-scoped layer around external interaction.

## Install

```
pip install curiosity-cat
npm install curiosity-cat
```

The minimum useful install is smaller still: copy `standing-orders/general-safety.md` into an agent's system prompt. No account, no API key. For real enforcement on Claude Code, install the CLI and run `compile` and `prove`.

MIT licence. Available in English, Arabic, Mandarin and Hindi.

## The app, in preview

A macOS app is in final testing. It discovers every agent on the machine, shows one guard board — what's protected, from what, since when — and lets an operator assign a proven profile to an agent in one click, with backup and undo. It is not yet released; nothing here should be read as a shipping date.

## Roadmap, without promises

Additional compile targets are under evaluation — no date, no ordering commitment; targets earn a compiler one at a time, and this document will say so honestly when one ships. The Danger Map, a shared close-call register anchored to MITRE ATLAS and NIST AI RMF, is live and growing as reports come in. Telemetry and any data leaving an operator's machine stay off by default and gated behind explicit consent controls as those features ship — none is collected today. None of this is a commitment to a date. It's a direction, stated plainly as a direction.

---

*Curiosity Cat is a Short+Sweet International product.*
*curiositycat.online · github.com/markscleary/Curiosity-Cat · curiosity@shortandsweet.org*
