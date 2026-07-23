#!/usr/bin/env python3
"""Scripted capture of the Curiosity Cat Guard Board window, for the site.

Launches the built (or installed) app straight to the Guard Board — a
*returning* launch (marker present) rather than the first-run flow — inside a
THROWAWAY $HOME so it never reads or writes the real ~/.hermes or
~/Library/Application Support (APP_SPEC / house rule: tests use temp dirs
only). Waits for the window, resolves its id with tools/find_window.swift,
captures just that window with `screencapture -l`, and verifies the PNG is
not blank.

The capture step needs macOS Screen Recording permission for whatever process
runs this script. If that grant is missing, screencapture yields an empty /
uniform image and this script exits 3 with a clear "blocked on Screen
Recording TCC" message — the harness is otherwise complete and re-runnable the
moment the grant lands.

Usage:
  python3 tools/screenshot_guard_board.py [--out PATH] [--app PATH]
      [--home DIR] [--profile DIR] [--settle SECONDS]

  --app   .app bundle to launch (default: freshly built repo bundle;
          falls back to /Applications/Curiosity Cat.app)
  --home  throwaway HOME to use (default: a fresh temp dir, deleted after)
  --profile  profile dir the board loads its estate from (default: empty temp
             dir -> board renders its own "Loading estate…" placeholder). Point
             this at a representative demo profile for a populated site shot.
  --out   where to write the PNG (default: ./screenshots/guard-board.png)
"""
import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SWIFT_HELPER = REPO_ROOT / "tools" / "find_window.swift"
PREFLIGHT_HELPER = REPO_ROOT / "tools" / "screen_recording_ok.swift"
BUILT_BUNDLE = REPO_ROOT / "app" / "src-tauri" / "target" / "release" / "bundle" / "macos" / "Curiosity Cat.app"
INSTALLED_BUNDLE = Path("/Applications/Curiosity Cat.app")
SCREENCAPTURE = "/usr/sbin/screencapture"
APP_SUPPORT_SUBPATH = ("Library", "Application Support", "online.curiositycat.shell")


def _resolve_bundle(arg):
    if arg:
        return Path(arg)
    if BUILT_BUNDLE.exists():
        return BUILT_BUNDLE
    if INSTALLED_BUNDLE.exists():
        return INSTALLED_BUNDLE
    sys.exit(f"no app bundle found (looked at {BUILT_BUNDLE} and {INSTALLED_BUNDLE})")


def _seed_home(home: Path, profile_dir: Path):
    appsup = home.joinpath(*APP_SUPPORT_SUBPATH)
    appsup.mkdir(parents=True, exist_ok=True)
    (appsup / "first-run-complete").write_bytes(b"")  # returning launch -> board
    (appsup / "last-profile.json").write_text(json.dumps({"profile_dir": str(profile_dir)}))


def _screen_recording_granted():
    """CGPreflightScreenCaptureAccess() via a tiny Swift helper — true iff the
    process running this harness already holds Screen Recording permission."""
    out = subprocess.run(["swift", str(PREFLIGHT_HELPER)], capture_output=True, text=True)
    return out.returncode == 0


def _find_window(owner="curiosity"):
    out = subprocess.run(
        ["swift", str(SWIFT_HELPER), owner], capture_output=True, text=True
    )
    if out.returncode != 0 or not out.stdout.strip():
        return None
    wid, x, y, w, h = out.stdout.split()
    return {"id": int(wid), "x": int(x), "y": int(y), "w": int(w), "h": int(h)}


def _is_blank(png_path: Path):
    """True if the capture looks empty/denied. Uses per-channel std-dev and
    distinct-colour count on a downscaled copy — a real UI screenshot has many
    colours and high variance; a TCC-denied or empty capture is near-uniform.
    """
    from PIL import Image
    import numpy as np
    img = Image.open(png_path).convert("RGB")
    small = img.resize((min(img.width, 320), min(img.height, 240)))
    arr = np.asarray(small, dtype=np.float64)
    std = float(arr.reshape(-1, 3).std(axis=0).mean())
    distinct = len({tuple(p) for p in np.asarray(small).reshape(-1, 3)[::7]})
    return (std < 4.0 or distinct < 12), std, distinct


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO_ROOT / "screenshots" / "guard-board.png"))
    ap.add_argument("--app", default=None)
    ap.add_argument("--home", default=None)
    ap.add_argument("--profile", default=None)
    ap.add_argument("--settle", type=float, default=2.0)
    ap.add_argument("--launch-timeout", type=float, default=15.0)
    args = ap.parse_args()

    bundle = _resolve_bundle(args.app)
    exe = bundle / "Contents" / "MacOS" / "curiosity-cat"
    if not exe.exists():
        sys.exit(f"no executable at {exe}")

    if not _screen_recording_granted():
        print("blocked-on-Mark:screen-recording-tcc")
        print("Screen Recording permission is NOT granted to the process running this")
        print("harness (CGPreflightScreenCaptureAccess() == false). Grant it once under")
        print("System Settings > Privacy & Security > Screen Recording, then re-run.")
        sys.exit(3)

    tmp_owner = None
    home = Path(args.home) if args.home else Path(tmp_owner := tempfile.mkdtemp(prefix="ccat-shot-")) / "home"
    profile_dir = Path(args.profile) if args.profile else Path(tempfile.mkdtemp(prefix="ccat-shot-prof-"))
    home.mkdir(parents=True, exist_ok=True)
    profile_dir.mkdir(parents=True, exist_ok=True)
    _seed_home(home, profile_dir)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    env = {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "HOME": str(home),
        "USER": os.environ.get("USER", "tester"),
    }
    log = tempfile.NamedTemporaryFile(prefix="ccat-shot-log-", suffix=".out", delete=False)
    proc = subprocess.Popen(
        [str(exe)], cwd="/", env=env, stdout=log, stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    exit_code = 0
    try:
        # wait for the board window to be logged
        deadline = time.monotonic() + args.launch_timeout
        shown = False
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                sys.exit(f"app exited early ({proc.returncode}); log:\n{Path(log.name).read_text(errors='replace')}")
            if "WINDOW_SHOWN label=board" in Path(log.name).read_text(errors="replace"):
                shown = True
                break
            time.sleep(0.2)
        if not shown:
            sys.exit(f"board window never announced; log:\n{Path(log.name).read_text(errors='replace')}")

        time.sleep(args.settle)  # let the webview paint

        win = _find_window("curiosity")
        if not win:
            sys.exit("could not resolve the Curiosity Cat window id (find_window.swift found nothing)")

        # -o: no shadow; -l: this window id; -x: silent
        cap = subprocess.run(
            [SCREENCAPTURE, "-x", "-o", "-t", "png", f"-l{win['id']}", str(out_path)],
            capture_output=True, text=True,
        )
        if cap.returncode != 0 or not out_path.exists():
            msg = (cap.stderr or "") + (cap.stdout or "")
            if "could not create image" in msg:
                print("blocked-on-Mark:screen-recording-tcc")
                print(f"screencapture could not read the window (rc={cap.returncode}): {msg.strip()}")
                print("Screen Recording permission is missing for the capturing process.")
                sys.exit(3)
            sys.exit(f"screencapture failed rc={cap.returncode}: {cap.stderr}")

        blank, std, distinct = _is_blank(out_path)
        from PIL import Image
        w, h = Image.open(out_path).size
        print(f"window id={win['id']} bounds={win['x']},{win['y']} {win['w']}x{win['h']}")
        print(f"wrote {out_path} ({w}x{h}px) std={std:.2f} distinct={distinct}")
        if blank:
            print("VERDICT: BLANK/DENIED — capture has no window content.")
            print("This is the Screen Recording TCC grant missing for the capturing process.")
            print("blocked-on-Mark:screen-recording-tcc")
            exit_code = 3
        else:
            print("VERDICT: OK — captured a non-blank Guard Board window.")
    finally:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(timeout=5)
        try:
            os.unlink(log.name)
        except OSError:
            pass
        if tmp_owner:
            shutil.rmtree(tmp_owner, ignore_errors=True)
        if not args.profile:
            shutil.rmtree(profile_dir, ignore_errors=True)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
