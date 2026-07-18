# Curiosity Cat — Media FAQ

Questions we expect from journalists, analysts and developers. Answers in Mark's voice.

---

**Why should I trust a theatre company with AI safety?**

Fair question. Short+Sweet has spent 25 years running rooms where thousands of people with different risk appetites do brave work without anyone getting hurt — that is safety culture, built and operated, not theorised. And we are operators before we are vendors: we run our own agent fleet on a Mac Mini and kept hitting the problem ourselves. Curiosity Cat is built by people with the problem, for people with the problem. Then judge us the way we ask to be judged: don't trust the story, run `prove` and read the Clean Bill.

---

**What does `prove` actually prove?**

Two different things, and the report never blurs them. Self-consistency trials replay the compiled rules against themselves — they prove the file says what the compiler intended. The observed-deny trial is different: a real, live agent session is asked to do the forbidden thing, and we record the refusal. Only that proves a running agent was actually stopped. Every line of every Clean Bill is labelled as one or the other. When we can't run the live trial safely, the report says the weaker thing, in plain words.

---

**Has the proof layer ever caught anything real?**

Yes — us. Its first observed trial failed our own build: a sandbox setting in the compiler quietly bypassed the deny rules. Every assertion said safe; the live trial said no. We fixed it before release. That episode is why the product's law is proven, not asserted — an assertion-only tool would have shipped that hole.

---

**Doesn't the agent platform already have safety features?**

The platform's safety training governs what the model chooses to do. It doesn't govern what your machine lets the agent do — and the platforms say so: Anthropic's documentation notes there is no sandbox between Computer Use and what's on your screen. That's the boundary where Curiosity Cat starts: real permission rules on your machine, proven against a live session.

---

**Is a Clean Bill a certification?**

No. It is a dated report of trials that ran on your machine against your profile — and it can fail. A certification is someone's promise; a Clean Bill is a record of what held and what didn't, with the honest label on every line. We think that's worth more.

---

**What about agents other than Claude Code?**

One compile target ships today: Claude Code. Everything else runs on standing orders — briefing language that drops into any agent's system prompt, labelled as guidance because that's what it is. Targets earn compilers one at a time, and until a framework has one we won't pretend otherwise.

---

**What does it cost?**

Nothing. MIT licence, source on GitHub. Install it, fork it, ship it inside your own products. We're building the accessible safety layer for operators no one else is building for; the business follows the trust, not the other way round.

---

**What's the app?**

A macOS app in final testing. It discovers every agent on your machine, shows one guard board — what's protected, from what, since when — and lets you assign a proven profile to an agent in one click, with backup and undo. The same law applies: the board shows the worst true state, never a comforting one.
