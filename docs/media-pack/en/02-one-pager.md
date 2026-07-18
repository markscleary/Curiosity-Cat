# Curiosity Cat — One-Pager

**Agent safety for the rest of us. Proven, not asserted.**

## What it is

Curiosity Cat is an open-source safety tool for people who run AI agents without a security team. You choose a risk level in plain language — Housecat, Alley Cat or Tiger — and Curiosity Cat compiles it into a real, hardened permission profile for your agent. Then it proves the profile: escape trials against its own walls, a dated Clean Bill of health if they hold, an honest account of which wall failed if they don't.

## The problem

An agent's safety training governs what the agent chooses to do. It does not govern what your machine lets the agent do — and the platforms are honest about the gap: Anthropic's documentation notes there is no sandbox between Computer Use and what's on your screen. Enterprise platforms close that gap with security teams. The solo operator has been offered advice.

## How it works

**Compile.** `curiosity-cat compile --level housecat --target claude-code` turns a one-word choice into a real settings file — allow, deny and ask rules, not a paragraph of advice.

**Prove.** `curiosity-cat prove` runs escape trials against the compiled profile. Self-consistency checks replay the rules against themselves; the observed-deny trial asks a live agent session to do the forbidden thing and records the refusal. The two are never conflated — that line is drawn on every report.

**Clean Bill.** Every trial lands in CLEAN-BILL.md, one sentence each, dated. A report that can fail — and says so when it does.

## Why believe it

The proof layer's first observed trial caught a real bug in our own compiler: a sandbox flag that bypassed the deny rules. The assertion said safe; the trial said no. That is why the product proves instead of asserting.

## Scope, honestly

One compile target today: Claude Code. Everything else runs on standing orders — guidance, clearly labelled as guidance, until it gets its own compiler. A macOS app — fleet discovery, one-click assignment, a live guard board — is in final testing.

## Install

```
pip install curiosity-cat
npm install curiosity-cat
```

MIT licence. English, Arabic, Mandarin, Hindi.

## Links

curiositycat.online · github.com/markscleary/Curiosity-Cat · publicist@shortandsweet.org
