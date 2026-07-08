# Curiosity Cat — App Spec v1 (APP_SPEC.md)
Decision log, 5 Jul 2026. Working decisions, reversible only by Mark.

FORM: macOS menu bar (tray) app. Tauri v2 shell over the site's existing HTML/CSS/JS character assets. Python engine bundled as PyInstaller sidecar (ccat-engine) speaking JSON over stdio. v1 fully local: no accounts, no cloud, free. Distribution: signed+notarised DMG + Homebrew cask + GitHub Releases with Tauri auto-updater. App Store deferred. Phone companion deferred; remote alarm optional via user-configured webhook.

LAYERS:
1. ENGINE (python, curiosity_cat/): refactor CLI internals into core library — compile_profile(level, target) -> ProfileDir; prove(profile_dir, observed=True) -> CleanBill; check(candidate) -> WhiskerVerdict (Danger Map lookup); report_close_call(event) (consent-gated). Add `ccat-engine serve`: line-delimited JSON requests/responses over stdio for the shell. Honesty invariant carries over: verdict methods are always self-consistency vs observed-deny, never conflated.
2. WATCHER: compile --target claude-code additionally emits PreToolUse/PostToolUse hook entries into the generated settings.json, POSTing events to http://127.0.0.1:8377/event. Event schema: {ts, session, tool, input_digest, verdict: allowed|denied|held, threat_class?, profile_id}. Consumers: live feed (the Bell), close-call capture (denied events matching threat classes -> queued Danger Map report, user consent required before any submission), approval gate (PreToolUse on irreversible-class actions returns hold; app surfaces one-sentence Meow-spec prompt; timeout default = deny).
3. SHELL (Tauri v2): tray icon = cat state machine (asleep=housecat quiet; ears-up=activity; hackles=close call; mouse=tripwire/alarm). Windows: Slider (choose level -> engine compile -> shows PROFILE.md in C-Cat voice), Feed (the Bell, one human sentence per event; blocks rendered per Meow spec: what the cat tried / why the fence said no / what to do if you disagree), Clean Bill viewer with PNG share-card export ("my agent survived N escape attempts"), Settings (webhook, consent toggles, skins). First-run journey: 3 screens mirroring the site's 10-page structure compressed: choose your cat -> compile -> prove (watch the escape attempts live) -> Clean Bill.
4. CHARACTER SYSTEMS: weekly Purr — local scheduled digest, template-based Nine Lives voice, zero LLM dependency in v1. Skin-unlock system ported from site/js/skins.js as collectible layer. All copy obeys the honesty layer: flagged vs blocked vocabulary follows enforcement reality.

BRIEF SEQUENCE: APP-1 engine library+serve (branch app-v1 off accessible-layer-v1 AFTER ccat-al-5 fix). APP-2 watcher hooks+schema+reference listener. APP-3 Tauri scaffold+slider+tray states. APP-4 feed+Meow+approval gate. APP-5 share card+Purr. APP-6 packaging (BLOCKED on Mark: Apple Developer ID). APP-7 site download page (post PR-merge).
HUMAN DEPENDENCIES: Apple Developer ID at APP-6. Trademark filing (separate track). Monetisation decision deferred by design.

## Network Layer Principles

Binding on all future briefs/instances touching the Danger Map network layer (report collection, warnings distribution, telemetry) — the reporting/watching client and the receiving service alike.

a. **Consent as architecture** — nothing leaves the machine without an explicit human tap, ever. No background auto-submission, no "send by default," no dark patterns that make declining harder than accepting.
b. **Pattern not payload** — reports carry `threat_class`, `indicator`, `platform`, `profile_version` only; never prompts, paths, file contents, or user context. The outward-facing warnings feed enforces this at the read boundary regardless of what the write boundary currently accepts.
c. **Corroboration before escalation** — a threat escalates on multiple independent observed reports, never one.
d. **Observed vs suspected report grades are distinct end to end** — the `grade` field is never inferred, defaulted away, or blurred between collection, storage, and the warnings feed.
e. **C-Cat proposes, the human disposes** — no silent profile rewrites, no auto-submission. Every report and every clean bill submission is something the operator explicitly saw and approved before it left the machine.
f. **Clean Bills are versioned telemetry** — wall x platform_version x held/failed enables fleet-level platform-drift detection: a wall that quietly stops holding across many machines on the same platform version is a signal, not noise.
