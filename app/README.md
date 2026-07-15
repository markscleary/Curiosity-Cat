# Curiosity Cat — App Shell

Tauri v2 menu bar (tray) shell for Curiosity Cat, macOS only in v1.
APP-3 (see `../docs/app/APP_SPEC.md`, Shell section) built the tray icon
state machine, the Slider window, and the first-run journey, plus a
read-only Feed stub. APP-4 made the Feed live, enforced the Meow spec
app-wide, and wired the approval gate. APP-5 added share-card export and
the weekly Purr. APP-6 built the PyInstaller sidecar, an unsigned release
build (.app + DMG), the Homebrew cask draft, and the updater config —
everything distribution-shaped short of Apple credentials. Signing and
notarisation are the one remaining step, blocked on Mark having an Apple
Developer ID (`docs/app/SIGNING.md`). APP-B1 polished the Feed and gave
the tray icon a real state machine (see below).

## What APP-B1 added

- **A real tray state machine** (`js/tray-state.js`): a pure, DOM-free
  module — testable under plain Node (`tests/js/test_tray_state.js`, `node
  --test tests/js`) — that folds each poll's new Watcher events onto a
  decaying "heat" score and picks the tray glyph
  (`asleep`/`ears-up`/`hackles`/`mouse`) plus a 0..1 `pitch`. A burst of
  close calls compounds (pitch/urgency rises "as events approach the fence
  line"); one stray allowed event right after doesn't instantly cool the
  tray back down. `feed.js` sets `--pitch` as a CSS custom property each
  poll, so the Feed card itself glows hotter red the closer things get to
  the fence, not just the tray glyph.
- **A more readable Feed**: the Watcher listener's `/events` response now
  carries `meow_lines` alongside `meow` (`meow.format_event_lines`,
  additive — never a second source of truth for the wording, still
  `meow.py` only) so a denied block's three sentences (what tried / why no
  / what to do) render as three separate paragraphs instead of one dense
  run-on line.

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
    board.html            the Guard Board — the estate list + whole-fleet
                          protect/undo actions, the app's landing view
                          (APP-G1, tray menu's "Guard Board")
    slider.html          the Slider window
    feed.html             the Feed — live Watcher stream, Meow blocks (APP-4)
    approval.html          the approval gate's Allow/Deny dialog (APP-4)
    purr.html               This Week's Purr window (APP-5)
    firstrun/
      choose.html          screen 1: pick housecat / alleycat / tiger
      compile.html          screen 2: compile via the sidecar
      prove.html             screen 3: pick a discovered target, apply,
                              stream trials live, end on Clean Bill,
                              export a share card (APP-5)
    css/adventure-slider.css   ported verbatim from site/css/adventure-slider.css
    js/
      adventure-slider.js       ported slider drag/click/keyboard behaviour
      sidecar-client.js          thin wrapper over the sidecar_call Tauri command
      board.js                    Guard Board: estate list, fleet-wide protect/undo (APP-F1/APP-G1)
      feed.js                     polls the Watcher listener, drives tray state (APP-4/APP-B1)
      tray-state.js                 pure tray state machine, node-testable (APP-B1)
      approval.js                  the approval dialog's Allow/Deny logic (APP-4)
      purr.js                       fetches This Week's Purr once (APP-5)
```

## Prerequisites

- Rust + Cargo (`brew install rust`, or rustup)
- Node (for the `@tauri-apps/cli`, run via `npx` — no project-local
  `package.json`/`node_modules` needed for v1)
- The `curiosity-cat` Python package installed somewhere on `PATH` as the
  `curiosity-cat` CLI (`watcher.rs` spawns
  `curiosity-cat listen --profile <dir>` — this is not yet bundled, see
  "Known gap" below). `ccat-engine`, the sidecar, no longer needs a PATH
  install — see below.

## Sidecar: ccat-engine

`ccat-engine` ships as a PyInstaller onefile binary, bundled as a Tauri
[external binary](https://v2.tauri.app/develop/sidecar/) rather than
resolved on `PATH`. Build it once (from the repo root):

```sh
app/packaging/build-sidecar.sh
```

This creates a build-only venv under `app/packaging/.build-venv`
(`pip install -e .` + `pyinstaller`), runs
`app/packaging/ccat-engine.spec`, and copies the result into
`app/src-tauri/binaries/ccat-engine-<target-triple>` — the name
`bundle.externalBin` (`tauri.conf.json`) and `capabilities/default.json`'s
`shell:allow-execute` grant both expect. `tauri-build`'s `build.rs` step
then copies/renames that binary next to the compiled Rust binary for
every `cargo build`/`cargo tauri dev`/`cargo tauri build`, so this is a
one-time step per target triple, not a per-build one — re-run it only
after changing `curiosity_cat/serve.py` or its dependencies.

`sidecar.rs` spawns it via `tauri_plugin_shell`'s `ShellExt::sidecar()`
(an async, event-stream API — `CommandEvent::Stdout`/`Stderr` — replacing
the earlier blocking `std::process::Command` + `BufReader`); the
line-delimited JSON call contract itself
(`call(method, params) -> Result<Value, String>`) is unchanged. If the
sidecar binary is missing, `sidecar::init` logs to stderr and every
sidecar-backed command (compile/prove/etc.) returns a clear error rather
than crashing the app.

**Known gap:** only `ccat-engine` is packaged this way. The Watcher
listener (`curiosity-cat listen`, `watcher.rs`) still shells out to
`curiosity-cat` on `PATH` — a signed/notarised build handed to someone
without a local Python install would have a working Slider/Feed but no
live watcher. Packaging that as a second sidecar is follow-up work, not
part of this brief.

## Dev launch

Build the sidecar once (see above — re-run it after changing
`curiosity_cat/serve.py` or its dependencies), then:

```sh
cd app
npx --yes @tauri-apps/cli@2 dev
```

This runs the same Rust shell — tray, sidecar, watcher, first-run routing —
against `src/` directly. There's no `devUrl`/bundler step; `build.frontendDist`
(`../src`) is the only frontend source for both dev and release builds, so
`tauri dev` serves those static files as-is with no HMR — edit
`src/**/*.html`/`*.js`, then reopen the window (tray menu, or quit/relaunch)
to see the change. Rust changes under `src-tauri/` are picked up
automatically: `tauri dev` recompiles and relaunches the app on save.
`curiosity-cat` itself (the Watcher listener `watcher.rs` spawns) still
needs to be on `PATH` for the Feed to go live — `pip install -e .` from the
repo root, same as any other local run of the CLI.

## Building

```sh
cd app
npx --yes @tauri-apps/cli@2 build          # unsigned release build: .app + .dmg
# or: build --debug                        # .app only (bundle.targets includes dmg
                                            # regardless, but --debug skips it)
```

Produces `src-tauri/target/release/bundle/macos/Curiosity Cat.app` and
`src-tauri/target/release/bundle/dmg/Curiosity Cat_0.1.0_aarch64.dmg`.
Unsigned: macOS Gatekeeper will quarantine both until ad-hoc/Developer-ID
signed — see `docs/app/SIGNING.md`.

## macOS signing / notarisation (deferred to APP-6 signing gate)

Not done in this brief — blocked on Mark obtaining an Apple Developer ID
(`docs/app/APP_SPEC.md` HUMAN DEPENDENCIES). Full commands in
`docs/app/SIGNING.md`; summary:

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
complete and opens the Guard Board; from then on the tray icon is the
only way in.

## Where profiles live

Two separate "home" directories exist — easy to conflate, since both hold a
`profiles/` directory produced by the same `core.compile_profile()`:

- **The `curiosity-cat` CLI's own default home**
  (`curiosity_cat/core.py` `resolve_home()`), used for any terminal-run CLI
  command that doesn't pass `--profiles-dir`: first `$CURIOSITY_CAT_HOME` if
  set, else an already-existing `./curiosity-cat` in a writable cwd, else
  `~/Library/Application Support/Curiosity Cat` on macOS.
  `profiles/`, `standing-orders/`, `policies/`, `quarantine/`, `logs/`, and
  `registry.json` all live under here.
- **The app's own data dir** — a Tauri `app_data_dir()`, which on macOS
  resolves from `tauri.conf.json`'s `identifier`
  (`online.curiositycat.shell`) to
  `~/Library/Application Support/online.curiositycat.shell/`. Every
  `compile` call the app makes passes this directory explicitly as
  `profiles_dir` (`commands.rs`'s `profiles_dir_path`, via
  `sidecar-client.js`) rather than letting `ccat-engine` fall back to its
  own cwd-derived default — a Finder launch gives the sidecar process cwd
  `/` (read-only), which is the bug this explicit pass-through avoids. So
  profiles compiled by the app land under
  `.../online.curiositycat.shell/profiles/`, a different directory tree
  from the CLI's own home, even though it's the same `compile_profile()`
  underneath. `first-run-complete` and `last-profile.json`
  (`commands.rs`'s `marker_path`/`last_profile_path`) live alongside it.

Point either one anywhere with `$CURIOSITY_CAT_HOME` (CLI) or by inspecting
`get_profiles_dir`'s return value (app, e.g. via the Feed/board's dev
console) — there is no cross-linking between the two by default.

## Command map: discover / apply / fleet / prove

Every verb below exists twice: once as a `curiosity-cat` CLI subcommand
(`curiosity_cat/cli.py`) for terminal use, once as a `ccat-engine` sidecar
JSON-RPC method (`curiosity_cat/serve.py`'s `METHODS`) the app calls via
`sidecar-client.js`/`window.CCAT.*`. Both paths call the same `core.py`
functions.

| Concept  | CLI                                                          | Sidecar (`window.CCAT.*`)         | Driven from (app)                          | What it does |
|----------|---------------------------------------------------------------|-------------------------------------|---------------------------------------------|--------------|
| Discover | `curiosity-cat estate`                                       | `estate()`                          | Guard Board (`board.js`) on load; `firstrun/prove.html`'s target picker | Lists every protectable target (Claude Code projects, `~/.claude` global, agent processes, MCP servers) and its guarded/unguarded state. Read-only. |
| Apply    | `curiosity-cat apply --level <l> --target <path\|global>`    | `apply(profileDir, target)`         | `firstrun/prove.html`'s "Apply" button (single target, first run) | Installs a compiled profile's `settings.json` into one target (backing up whatever was there), then proves it. |
| Fleet    | `curiosity-cat fleet --level <l> [--undo]`                   | `fleet(level, observed, targets)` / `fleetUndo(targets)` | Guard Board's "Protect whole fleet" / "Undo whole fleet" buttons | Applies-and-proves `<level>` against every discovered, applicable target in one pass, or restores every guarded target's pre-apply backup. |
| Prove    | `curiosity-cat prove --profile <dir> [--target <path\|global>]` | `prove(profileDir, observed, target)` | `firstrun/prove.html`, right after Apply     | Runs self-consistency + (unless skipped) one live observed trial, writing a Clean Bill. |

`unapply` (`curiosity-cat unapply --target ...` / `unapply(target)`)
restores a single target's pre-apply backup, the one-target counterpart to
Fleet's `--undo` — implemented in `sidecar-client.js` but not yet wired to
any app screen (no per-target undo button exists outside Fleet's
whole-estate undo).
