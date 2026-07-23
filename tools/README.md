# tools/

## screenshot_guard_board.py — scripted Guard Board capture (for the site)

Launches the built (or `/Applications`) Curiosity Cat app straight to the
**Guard Board** — a *returning* launch, not the first-run flow — inside a
throwaway `$HOME`, so it never reads or writes the real `~/.hermes` or
`~/Library/Application Support` (house rule: only temp dirs). It waits for the
board window (`WINDOW_SHOWN label=board`), resolves that window's id with
`find_window.swift`, captures just that window via `screencapture -l`, and
verifies the PNG isn't blank.

```
python3 tools/screenshot_guard_board.py \
    --out ./screenshots/guard-board.png \
    [--app "/Applications/Curiosity Cat.app"] \
    [--profile /path/to/demo-profile] \
    [--settle 2.0]
```

Exit codes: `0` clean capture · `3` blocked on Screen Recording TCC · other = error.

### Requires a one-time Screen Recording grant (blocked-on-Mark)

macOS gates all window/screen capture behind **Screen Recording** permission,
granted per-application to whatever process runs the harness. The harness
preflights with `CGPreflightScreenCaptureAccess()` and, if the grant is
missing, prints `blocked-on-Mark:screen-recording-tcc` and exits 3 without
launching anything.

Grant once under **System Settings → Privacy & Security → Screen Recording**
for the process you run it from (e.g. Terminal/iTerm if run by hand, or the
launchd MCP-bridge service if run under automation), then re-run — no code
change needed.

### Populated vs empty board

Default `--profile` is an empty temp dir, so the board renders its own
"Loading estate…" placeholder. For a representative site shot, point
`--profile` at a demo profile with real targets. (A dedicated demo fixture is
a sensible follow-up.)

## find_window.swift / screen_recording_ok.swift

Dependency-free Swift helpers (no pip/pyobjc): resolve an on-screen window id
by owner name, and preflight Screen Recording permission. Owner/id/bounds are
readable without the TCC grant; only the capture needs it.
