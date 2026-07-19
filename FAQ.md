# Frequently Asked Questions

## What is Curiosity Cat?

An open-source safety tool for people who run AI agents without a security team. It compiles a plain-language risk choice — Housecat, Alley Cat or Tiger — into a real, hardened permission profile for the agent, then proves the profile with escape trials instead of just asserting it's safe.

## How do I install it?

```
pip install curiosity-cat
npm install curiosity-cat
```

The minimum useful install is smaller: copy `standing-orders/general-safety.md` into your agent's system prompt. No account, no API key, sixty seconds. For real enforced permissions on Claude Code, install the CLI and run `compile` and `prove`.

## What do the risk levels mean?

Housecat, Alley Cat and Tiger — the adventure slider. Housecat confines the agent to reads and writes within the project and fetches from an explicit domain allowlist. Tiger widens that range. Credential paths — SSH keys, `.env` files, cloud config — are denied at every level; the slider changes how far the agent explores, not that floor.

## What does `prove` actually prove?

Two different things, and the report never blurs them. Self-consistency checks replay the compiled rules against themselves in a throwaway sandbox — they confirm the settings file says what the compiler intended. The observed-deny trial is different: where it's safe, `prove` spawns a real, non-interactive Claude Code session inside the compiled profile, asks it to attempt exactly one denied action, and records whether it was actually stopped. Only the observed trial proves a running agent was stopped. Every line of every Clean Bill says which kind it is.

## What happens if a Clean Bill fails?

`prove` exits nonzero and names the wall that failed — no safe claim gets written. A Clean Bill is a dated report of trials that ran against your profile, and it can fail. That's deliberate: the first time we ran a genuine observed trial against our own compiler, it found a bug — a malformed sandbox setting quietly bypassed the deny rules while every self-consistency check still passed. We fixed it before release and kept the lesson as law: proven, not asserted.

## Does it back up my settings, and can I undo a change?

The macOS app, in final testing, assigns a compiled profile to an agent with backup and undo — your prior settings are saved before a profile is applied, and you can revert. That app hasn't shipped yet; the CLI's `compile` writes each profile to its own dated, versioned directory rather than overwriting anything in place.

## What about agents other than Claude Code?

One compile target ships today: Claude Code, with a real settings file — allow, deny and ask rules a framework actually enforces. Everything else — OpenClaw, Nanobot, LangChain, CrewAI, AutoGen, or any framework that accepts a system prompt — runs on Curiosity Cat's standing orders: plain-text briefing language, clearly labelled as guidance, not enforcement. Targets earn a compiler one at a time, and we won't claim otherwise until one does.

## Does Curiosity Cat collect any telemetry?

No, not today. Nothing is collected or sent off your machine by default. Any future telemetry will be off by default and gated behind explicit consent controls as those features ship — this document will say so plainly when that changes, not before.

## Is the Danger Map the same as telemetry?

No. The Danger Map is an opt-in shared close-call register — reports you choose to submit, structured and anonymised, with identity, credentials, IPs and free text excluded by design. It's separate from telemetry and off unless you turn it on.

## Is this a certification?

No. A Clean Bill is a dated record of trials that ran on your machine against your profile, and it can fail. A certification is a promise. This is a report of what held and what didn't, labelled honestly line by line.

## What does it cost?

Nothing. MIT licence, source on GitHub. Install it, fork it, ship it inside your own products.

## Can I contribute?

Yes. Framework adapters, policy packs, translations, stories and threat reports are all welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). Active contributors earn Quines, a non-financial credential that becomes trust reputation in the Danger Map.

## What languages does it support?

English, Arabic, Mandarin and Hindi at launch. Additional languages are added as the community contributes translations.

## Is there a graphical app, or is this CLI-only?

Today it's CLI-only: `compile`, `prove`, and the standing orders you paste by hand. A macOS app — fleet discovery, one-click profile assignment with backup and undo, a live guard board — is in final testing and not yet released.
