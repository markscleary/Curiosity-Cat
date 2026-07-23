"""Release gate: the built .app must run with zero dependence on pip, the
source checkout, or the repo cwd (APP-BUILD-3), and must actually show a
window on launch (APP-BUILD-4) — for BOTH the first-run journey AND every
later ("returning") launch.

Regression 1 (APP-BUILD-3): a bundle copied out of the dev tree and launched
with the repo entirely off PATH/PYTHONPATH used to print "could not start
watcher listener ... is the curiosity-cat package installed (`pip install
-e .`)?" and never bring up a live Watcher, because watcher.rs shelled out
to a PATH-resolved `curiosity-cat` CLI instead of the bundled `ccat-engine`
sidecar. This test ditto's the built bundle to a temp dir outside the repo
and launches the copy with a stripped environment to prove that's no longer
true.

Regression 2 (APP-BUILD-4): a healthy engine/watcher chain said nothing
about whether a window was ever created — main.rs only opened a window for
the first-run journey, so every *returning* launch was silently windowless.
commands::show_window now prints `WINDOW_SHOWN label=<label>` on stdout
whenever a window is created or re-shown.

Why this file is parametrized: is_first_run() in commands.rs is
`!marker_path().exists()`, where the marker is app_data_dir()/
first-run-complete. An earlier version of this gate only ever seeded
last-profile.json, so is_first_run() stayed true and every launch took the
always-worked `firstrun` branch — the `board` branch APP-BUILD-4 added for
returning launches (the exact bug: "app runs, engine healthy, but no
window") was never exercised and the gate passed blind. We now run both
scenarios and assert the *specific* window label each must show:
  - first-run  (no marker)  -> WINDOW_SHOWN label=firstrun
  - returning  (marker set) -> WINDOW_SHOWN label=board

Every path here — the copied bundle, its fake $HOME (which redirects both
Tauri's app_data_dir and any Python-side home resolution), the seeded
profile dir, the marker — lives under `tmp_path`. Nothing in this file ever
reads or writes the real ~/.hermes or ~/Library/Application Support.
"""

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_PATH = REPO_ROOT / "app" / "src-tauri" / "target" / "release" / "bundle" / "macos" / "Curiosity Cat.app"
LAUNCH_TIMEOUT_SECONDS = 15
POLL_INTERVAL_SECONDS = 0.2

WATCHER_ERROR_MARKERS = ("could not start watcher listener", "pip install -e .")
WINDOW_SHOWN_MARKER = "WINDOW_SHOWN"
APP_SUPPORT_SUBPATH = ("Library", "Application Support", "online.curiositycat.shell")
FIRST_RUN_MARKER_FILE = "first-run-complete"


def _requires_bundle():
    if sys.platform != "darwin":
        pytest.skip("Curiosity Cat is macOS-only (APP_SPEC.md FORM)")
    if not BUNDLE_PATH.exists():
        pytest.skip(f"no release bundle at {BUNDLE_PATH} — run `npx --yes @tauri-apps/cli@2 build` in app/ first")


def _ps_lines():
    return subprocess.run(
        ["ps", "-Ao", "pid,ppid,command"], capture_output=True, text=True, check=True
    ).stdout.splitlines()


def _stripped_launch_env(fake_home):
    """An environment with the repo checkout entirely off PATH/PYTHONPATH,
    and $HOME redirected to a throwaway directory so neither Tauri's
    app_data_dir() (`dirs::data_dir()`, which reads $HOME) nor any
    Python-side default-home resolution can reach the real
    ~/Library/Application Support or ~/.hermes.
    """
    return {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "HOME": str(fake_home),
        "USER": os.environ.get("USER", "tester"),
    }


@pytest.fixture
def copied_bundle(tmp_path):
    _requires_bundle()
    dest_dir = tmp_path / "foreign-install"
    dest_dir.mkdir()
    dest_app = dest_dir / "Curiosity Cat.app"
    subprocess.run(["ditto", str(BUNDLE_PATH), str(dest_app)], check=True)
    assert not str(dest_app).startswith(str(REPO_ROOT)), "copy must land outside the repo"
    return dest_app


@pytest.mark.parametrize(
    "returning, expected_label",
    [
        pytest.param(False, "firstrun", id="first_run_shows_firstrun_window"),
        pytest.param(True, "board", id="returning_launch_shows_board_window"),
    ],
)
def test_foreign_directory_launch_starts_watcher_and_shows_window(
    copied_bundle, tmp_path, returning, expected_label
):
    fake_home = tmp_path / "fake-home"
    app_support = fake_home.joinpath(*APP_SUPPORT_SUBPATH)
    app_support.mkdir(parents=True)

    # Seed last-profile.json in BOTH scenarios: main.rs's setup() reads it
    # (get_last_profile_dir) and calls watcher::restart() immediately, which
    # is the APP-BUILD-3 watcher regression. listen.py degrades gracefully
    # on an empty profile dir, so the dir needs no compiled contents.
    profile_dir = tmp_path / "seeded-profile"
    profile_dir.mkdir()
    (app_support / "last-profile.json").write_text(json.dumps({"profile_dir": str(profile_dir)}))

    # The single bit that selects first-run vs returning. is_first_run() is
    # `!marker_path().exists()` (commands.rs); seeding the marker makes this
    # a *returning* launch, which must land on the Guard Board (label=board)
    # rather than the first-run flow (label=firstrun).
    if returning:
        (app_support / FIRST_RUN_MARKER_FILE).write_bytes(b"")

    expected_line = f"{WINDOW_SHOWN_MARKER} label={expected_label}"

    exe = copied_bundle / "Contents" / "MacOS" / "curiosity-cat"
    assert exe.exists()

    stdout_path = tmp_path / "stdout.log"
    stderr_path = tmp_path / "stderr.log"
    with open(stdout_path, "wb") as stdout_f, open(stderr_path, "wb") as stderr_f:
        proc = subprocess.Popen(
            [str(exe)],
            cwd="/",
            env=_stripped_launch_env(fake_home),
            stdout=stdout_f,
            stderr=stderr_f,
            start_new_session=True,
        )

        try:
            deadline = time.monotonic() + LAUNCH_TIMEOUT_SECONDS
            engine_listen_pid = None
            window_shown = False
            while time.monotonic() < deadline and (engine_listen_pid is None or not window_shown):
                assert proc.poll() is None, (
                    f"app process exited early with code {proc.returncode} — "
                    f"stderr:\n{stderr_path.read_text(errors='replace')}"
                )
                for line in _ps_lines():
                    parts = line.split(None, 2)
                    if len(parts) != 3:
                        continue
                    pid, ppid, command = parts
                    if str(copied_bundle) in command and "ccat-engine" in command and "listen" in command:
                        if int(ppid) == proc.pid:
                            engine_listen_pid = int(pid)
                            break
                if not window_shown and expected_line in stdout_path.read_text(errors="replace"):
                    window_shown = True
                if engine_listen_pid is None or not window_shown:
                    time.sleep(POLL_INTERVAL_SECONDS)

            captured_stdout = stdout_path.read_text(errors="replace")
            captured_stderr = stderr_path.read_text(errors="replace")
            combined = captured_stdout + captured_stderr

            assert proc.poll() is None, f"app process died — stderr:\n{captured_stderr}"
            for marker in WATCHER_ERROR_MARKERS:
                assert marker not in combined, f"watcher error resurfaced: {marker!r} in output:\n{combined}"
            assert engine_listen_pid is not None, (
                f"no `ccat-engine listen` child of pid {proc.pid} within {LAUNCH_TIMEOUT_SECONDS}s — "
                f"stdout:\n{captured_stdout}\nstderr:\n{captured_stderr}"
            )
            assert expected_line in captured_stdout, (
                f"no {expected_line!r} within {LAUNCH_TIMEOUT_SECONDS}s — the app came up with a healthy "
                f"engine/watcher chain but never showed the expected {expected_label!r} window "
                f"(returning={returning}, APP-BUILD-4) — stdout:\n{captured_stdout}\nstderr:\n{captured_stderr}"
            )

            print(f"[test_app_bundle] scenario returning={returning} expected={expected_label!r}")
            print(f"[test_app_bundle] app pid={proc.pid} engine-listen pid={engine_listen_pid}")
            print(f"[test_app_bundle] stdout:\n{captured_stdout}")
            print(f"[test_app_bundle] stderr:\n{captured_stderr}")
        finally:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait(timeout=5)
