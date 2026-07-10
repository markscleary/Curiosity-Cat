# Curiosity Cat — App Shell

Tauri v2 menu bar (tray) shell for Curiosity Cat, macOS only in v1.
APP-3 (see `../docs/app/APP_SPEC.md`, Shell section) built the tray icon
state machine, the Slider window, and the first-run journey, plus a
read-only Feed stub. APP-4 made the Feed live, enforced the Meow spec
app-wide, and wired the approval gate. APP-5 (this brief) added share-card
export and the weekly Purr. Signed, notarised packaging is APP-6 (blocked
on Mark having an Apple Developer ID).

## What APP-4 added

- **Live Feed**: the shell spawns `curiosity-cat listen --profile <dir>`
  (`curiosity_cat/listen.py`) as its own background process
  (`src-tauri/src/watcher.rs`) whenever the active profile changes
  (`set_last_profile_dir`). The Feed window (`feed.html`/`js/feed.js`) is
  created hidden at app launch — not lazily on tray click — so its poll
  loop keeps running whether or not the window is visible, and polls the
  listener's `GET /events` directly over plain HTTP (CORS-open, loopback
  only) for one human sentence per event, colour-coded by verdict.
- **Meow spec, app-wide**: `curiosity_cat/meow.py` is the one place that
  renders events in Meow voice — one sentence normally, exactly three for a
  denied event (what the cat tried / why the fence said no / what to do if
  you disagree). Both the CLI's `curiosity-cat listen` and the Watcher
  listener the app spawns print through it, and the listener's `/events`
  response carries the already-formatted text, so the Feed never
  reimplements the voice in JS.
- **Approval gate**: irreversible-class Bash commands
  (`core.IRREVERSIBLE_HOLD_PATTERNS` — force-push, hard reset, branch -D)
  earn a `held` verdict from the PreToolUse hook
  (`curiosity_cat/events.py`), which then blocks on
  `curiosity_cat/gate.py`'s `request_decision()` — a synchronous HTTP round
  trip to the listener's `POST /event/hold`, which itself blocks
  server-side until a decision arrives or `listen.HOLD_WAIT_SECONDS` (20s)
  elapses, defaulting to deny either way. The hook's own compiled timeout
  (`core._WATCHER_GATE_TIMEOUT_SECONDS`, 30s for PreToolUse only —
  PostToolUse keeps the fast 2s budget) is sized to give that round trip
  room to finish. `feed.js` polls `GET /event/hold/pending` and opens a
  dedicated small always-on-top window (`approval.html`/`js/approval.js`,
  via the new `open_approval_window` command) per pending hold, showing the
  one-sentence Meow prompt with Allow/Deny buttons that POST directly to
  `/event/hold/<id>/decision`. That dialog is a plain Tauri `WebviewWindow`,
  not an OS-native `NSAlert` (no `tauri-plugin-dialog` dependency/capability
  surface was added for this brief) — revisit if a truly native alert is
  wanted later.
- Tray icon transitions (`ears-up`/`hackles`/`mouse`) are driven entirely
  from `feed.js`'s poll loop off what just arrived — no other window
  touches tray state.

## What APP-5 added

- **Share card export**: `curiosity_cat/card.py` renders any `clean-bill.json`
  into a PNG — a drawn cat glyph (vector shapes, not the 🐱 emoji, so it
  renders the same regardless of the host's font support), the level, the
  date, `curiositycat.online`, and a headline built only from
  `observed_trials` (never `self_consistency_trials` — those are reported
  on their own, clearly-labelled line, so the two counts can never read as
  one claim). The Clean Bill card in `firstrun/prove.html` calls it via a
  new `render_share_card` sidecar method (`window.CCAT.renderShareCard`),
  writing `share-card.png` alongside the `clean-bill.json` and showing the
  written path — no new Tauri capability surface (asset protocol, dialog
  plugin) was needed, since the engine already has full filesystem access
  to write there.
- **The Purr**: `curiosity_cat/purr.py` builds a one-paragraph, template-based
  weekly digest — zero LLM dependency — from two already-persisted local
  sources: `event-history.jsonl` (new: `listen.py`'s `_handle_event` now
  appends every event it receives to this file per-profile, since the live
  Feed's `_EventLog` is in-memory only and resets on restart) and the Mouse
  Tray. A new tray menu item, "This Week's Purr", opens `purr.html`
  (`js/purr.js`), which fetches the digest once via the sidecar's `purr`
  method rather than polling like the Feed does.

## Layout

```
app/
  src-tauri/          Rust shell (Tauri v2)
    src/
      main.rs          app bootstrap: tray, sidecar, watcher, first-run routing
      tray.rs           tray icon state machine (asleep/ears-up/hackles/mouse)
      sidecar.rs         spawns + talks to `ccat-engine serve`
      watcher.rs          spawns/restarts `curiosity-cat listen` (APP-4)
      commands.rs         Tauri commands the frontend calls via invoke()
    tray-icons/         placeholder monochrome SVG + runtime PNG per tray state
    icons/              app icon set (32/128/128@2x + icon.icns)
    tauri.conf.json
  src/                 static frontend, no bundler — served directly as frontendDist
    slider.html          the Slider window
    feed.html             the Feed — live Watcher stream, Meow blocks (APP-4)
    approval.html          the approval gate's Allow/Deny dialog (APP-4)
    purr.html               This Week's Purr window (APP-5)
    firstrun/
      choose.html          screen 1: pick housecat / alleycat / tiger
      compile.html          screen 2: compile via the sidecar
      prove.html             screen 3: stream trials live, end on Clean Bill,
                              export a share card (APP-5)
    css/adventure-slider.css   ported verbatim from site/css/adventure-slider.css
    js/
      adventure-slider.js       ported slider drag/click/keyboard behaviour
      sidecar-client.js          thin wrapper over the sidecar_call Tauri command
      feed.js                     polls the Watcher listener, drives tray state (APP-4)
      approval.js                  the approval dialog's Allow/Deny logic (APP-4)
      purr.js                       fetches This Week's Purr once (APP-5)
```

## Prerequisites

- Rust + Cargo (`brew install rust`, or rustup)
- Node (for the `@tauri-apps/cli`, run via `npx` — no project-local
  `package.json`/`node_modules` needed for v1)
- The `curiosity-cat` Python package installed somewhere on `PATH`, both as
  `ccat-engine` (the sidecar, see below) and as the `curiosity-cat` CLI
  itself (`watcher.rs` spawns `curiosity-cat listen --profile <dir>`) — the
  same `pip install -e ..` step below covers both console scripts.

## Sidecar: dev vs packaged

**Dev (now):** the app spawns whatever `ccat-engine` resolves to on `PATH`
(`app/src-tauri/src/sidecar.rs`). Install the engine into a virtualenv and
run Tauri with that venv's `bin/` prepended to `PATH`:

```sh
cd app
python3 -m venv .venv
.venv/bin/pip install -e ..
export PATH="$PWD/.venv/bin:$PATH"
npx --yes @tauri-apps/cli@2 dev      # or: build --debug
```

If `ccat-engine` isn't found, the shell logs a warning to stderr and every
sidecar-backed command (compile/prove/etc.) returns a clear error rather
than crashing the app — see `sidecar::init` / `sidecar::call`.

**Packaged (future, APP-6 territory):** replace the dev spawn with a
PyInstaller-built `ccat-engine` binary shipped as a Tauri
[external binary](https://v2.tauri.app/develop/sidecar/) (`bundle.externalBin`
in `tauri.conf.json`, invoked via `tauri_plugin_shell`'s sidecar API instead
of a bare `Command::new("ccat-engine")`). The call surface in `sidecar.rs`
(`call(method, params) -> Result<Value, String>`) does not need to change —
only how the child process is located and spawned. Steps when that lands:

1. `pyinstaller --onefile --name ccat-engine curiosity_cat/serve.py` (or a
   spec file) per target triple, output named per Tauri's sidecar
   convention (`ccat-engine-<target-triple>`).
2. Add the binary path to `tauri.conf.json`'s `bundle.externalBin`.
3. Swap `sidecar.rs`'s `Command::new("ccat-engine")` for
   `app.shell().sidecar("ccat-engine")` (`tauri-plugin-shell`), which
   resolves the bundled binary instead of searching `PATH`.

## Building

```sh
cd app
npx --yes @tauri-apps/cli@2 build --debug
```

Produces `src-tauri/target/debug/bundle/macos/Curiosity Cat.app`. DMG
bundling is left out of `bundle.targets` for now — it's a distribution
concern that belongs with APP-6 packaging, not this scaffold.

## macOS signing / notarisation (deferred to APP-6)

Not done in this brief — blocked on Mark obtaining an Apple Developer ID
(`docs/app/APP_SPEC.md` HUMAN DEPENDENCIES). For when that lands:

- `tauri.conf.json`'s `bundle.macOS.signingIdentity` (or the
  `APPLE_SIGNING_IDENTITY` env var) needs a "Developer ID Application"
  certificate in the login keychain.
- Notarisation needs an app-specific password or API key
  (`APPLE_ID`/`APPLE_PASSWORD`/`APPLE_TEAM_ID`, or
  `APPLE_API_KEY`/`APPLE_API_ISSUER`) and `tauri build` (not `--debug`) —
  Tauri staples the ticket automatically when those env vars are present.
  See https://v2.tauri.app/distribute/sign/macos/.
- The hardened runtime + entitlements: the sidecar is spawned as a plain
  child process (no XPC), so no extra entitlement should be needed beyond
  Tauri's default `entitlements.plist` — confirm this once a real signing
  identity is available, since unsigned dev builds never exercise the
  hardened-runtime restrictions that matter here (e.g. spawning
  unsigned/ad-hoc-signed child processes).
- Homebrew cask + GitHub Releases auto-updater distribution (per
  APP_SPEC.md's FORM line) also wait on this.

## First run

On first launch (no `first-run-complete` marker in the app's data dir), the
app opens straight to `firstrun/choose.html` instead of just sitting in the
tray. `firstrun/prove.html`'s "Meet your cat" button marks first-run
complete and opens the Slider window; from then on the tray icon is the
only way in.
