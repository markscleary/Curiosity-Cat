# The Show — Concept Explainer

Written as a companion to the Curiosity Cat launch materials. For journalists who ask about it by name.

---

## The problem

AI agents can do long tasks. Agents cannot do long tasks unattended. An agent running for eight hours without a human present will eventually hit a moment where it needs a decision. If no human is there, the agent either stops and wastes time or proceeds and makes a mess.

This is a coordination problem, not an intelligence problem. You cannot solve it with smarter models. You solve it with better orchestration.

## The Show

The Show is a framework for orchestrating AI agent task execution with authenticated operator escalation. The operator writes a programme — a sequence of scenes — and hands it to The Show. The Show runs the scenes in order, manages dependencies, handles failures, and when human decision is needed it sends an urgent contact through a signed channel (Telegram, email, SMS, WhatsApp) to the operator.

The operator can be at their desk or asleep or on a plane. The Show waits. The operator responds with a short authenticated answer — APPROVE, REJECT, STOP, CONTINUE — and The Show proceeds from wherever it paused.

This lets an operator dispatch a programme before bed and wake up to the work substantially done, with only the decisions that required their judgement escalated. The agent does not freeze waiting for permission. The operator does not spend their day approving micro-decisions. The Show handles everything in between.

## The theatrical metaphor

The Show borrows its vocabulary from theatre. Scenes. Programmes. Understudies. Stage managers. Urgent contacts. The metaphor is not decoration — it is load-bearing. Theatre has spent three thousand years solving the problem of coordinating many performers through a long performance with live decisions along the way. Stage managers call cues. Understudies step in when something fails. The show must go on, and the theatrical tradition tells us exactly what that means.

The Show the framework uses those patterns directly. When a scene fails, the understudy runs. When a critical decision arises, the stage manager escalates to the urgent contact. When the monitor detects runaway cost, it pauses the production mid-flight. The language is theatrical. The engineering is real.

## What it enables

The Show enables three things.

**First, unattended execution of long programmes.** An operator dispatches a programme at 9pm and sleeps. The Show runs overnight. When morning arrives, the operator wakes to the work done and the decisions they made by SMS at 2am recorded in the programme's journal.

**Second, human attention conservation.** The operator is only interrupted when a decision genuinely requires their judgement. Not for every tool call. Not for every action. Only for the scenes flagged as requiring authenticated human approval.

**Third, auditable agent work.** Every scene run, every failure, every escalation, every decision — all recorded. Six months later, the operator can reconstruct exactly what happened and why.

## How it relates to Curiosity Cat

Curiosity Cat is the safety layer. It watches the agent and enforces standing orders. The Show is the orchestration layer. It drives the agent through a planned programme and handles escalation.

An agent running under Curiosity Cat with The Show as its orchestrator is the current best practice for solo operators. The agent runs The Show's programme. The Show handles scene sequencing and escalation. Curiosity Cat watches every action and enforces the operator's risk appetite. The operator dispatches and sleeps. This stack is what Short+Sweet Agential is building for.

## Status

The Show is in development. First live rehearsal ran 19 April 2026. Core runtime (state machine, dependency resolver, adapter contracts, urgent contact authentication, crash-seam recovery) works and passes 231 tests. Current version is v1.0, locked and shipping incrementally.

Public release is planned for later in 2026. Current users are Short+Sweet International's internal operations. We are building in public and the code is open.

## Pronouncing the name

"The Show" is always spoken with the definite article. Not "Show." Not "Your Show." The Show. It is a proper noun. One framework, many productions run on it.
