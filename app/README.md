# Curiosity Cat — App Shell

Tauri v2 menu bar (tray) shell for Curiosity Cat, macOS only in v1. This is
APP-3 in the app sequence (see `../docs/app/APP_SPEC.md`, Shell section):
tray icon state machine, the Slider window, the first-run journey, and a
read-only Feed stub. The live Watcher feed, Meow-spec blocks and the
approval gate are APP-4. Share-card export and Purr are APP-5. Signed,
notarised packaging is APP-6 (blocked on Mark having an Apple Developer ID).

## Layout

```
app/
  src-tauri/          Rust shell (Tauri v2)
    src/
      main.rs          app bootstrap: tray, sidecar, first-run routing
      tray.rs           tray icon state machine (asleep/ears-up/hackles/mouse)
      sidecar.rs         spawns + talks to `ccat-engine serve`
      commands.rs         Tauri commands the frontend calls via invoke()
    tray-icons/         placeholder monochrome SVG + runtime PNG per tray state
    icons/              app icon set (32/128/128@2x + icon.icns)
    tauri.conf.json
  src/                 static frontend, no bundler — served directly as frontendDist
    slider.html          the Slider window
    feed.html             Feed window stub
    firstrun/
      choose.html          screen 1: pick housecat / alleycat / tiger
      compile.html          screen 2: compile via the sidecar
      prove.html             screen 3: stream trials live, end on Clean Bill
    css/adventure-slider.css   ported verbatim from site/css/adventure-slider.css
    js/
      adventure-slider.js       ported slider drag/click/keyboard behaviour
      sidecar-client.js          thin wrapper over the sidecar_call Tauri command
```

## Prerequisites

- Rust + Cargo (`brew install rust`, or rustup)
- Node (for the `@tauri-apps/cli`, run via `npx` — no project-local
  `package.json`/`node_modules` needed for v1)
- The `curiosity-cat` Python package installed somewhere on `PATH` as
  `ccat-engine` (see below)

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
