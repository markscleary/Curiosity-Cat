"""Release gate: the built .app must run with zero dependence on pip, the
source checkout, or the repo cwd (APP-BUILD-3), and must actually show a
window on launch (APP-BUILD-4).

Regression covered: a bundle copied out of the dev tree and launched with
the repo entirely off PATH/PYTHONPATH used to print
"could not start watcher listener ... is the curiosity-cat package
installed (`pip install -e .`)?" and never bring up a live Watcher, because
watcher.rs shelled out to a PATH-resolved `curiosity-cat` CLI instead of
the bundled `ccat-engine` sidecar. This test ditto's the built bundle to a
temp dir outside the repo and launches the copy with a stripped
environment to prove that's no longer true.

Second regression covered (APP-BUILD-4): the engine/watcher chain coming
up healthy said nothing about whether a window was ever created — main.rs
only opened a window for the first-run journey, so every later launch was
silently windowless. commands::show_window now prints `WINDOW_SHOWN` on
stdout whenever a window is created or re-shown; this test asserts that
line appears, not just that the watcher started.

Third regression covered (APP-BUILD-6): a real-user report of the Guard
Board rendering greyed behind a dead confirm/cancel modal traced to
sidecar.rs's `call()` having no bound at all on how long it would wait for
ccat-engine's stdout — a hung or unresponsive engine left "Protect/Undo
whole fleet" permanently disabled with no error, indistinguishable from a
dead button. `test_confirm_transport_round_trip_within_timeout` below drives
the exact stdio transport board.js's Confirm action uses (line-delimited
JSON to the built `ccat-engine` binary, the same one Tauri's sidecar spawns)
and asserts a response lands well inside the 5s bound sidecar.rs now
enforces — proving the wiring the Confirm button depends on actually
answers rather than dead-ending silently.

Every path here — the copied bundle, its fake $HOME (which redirects both
Tauri's app_data_dir and any Python-side home resolution), the seeded
profile dir — lives under `tmp_path`. Nothing in this file ever reads or
writes the real ~/.hermes or ~/Library/Application Support.
"""

import json
import os
import selectors
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


def test_foreign_directory_launch_starts_the_watcher_with_no_pip_dependence(copied_bundle, tmp_path):
    fake_home = tmp_path / "fake-home"
    (fake_home / "Library" / "Application Support" / "online.curiositycat.shell").mkdir(parents=True)

    # Seeds the exact condition the bug report reproduced: a profile already
    # marked active from a previous run, so main.rs's setup() calls
    # watcher::restart() immediately at launch (commands.rs's
    # get_last_profile_dir / set_last_profile_dir). The profile dir itself
    # doesn't need real compiled contents — listen.py degrades gracefully
    # (core-adjacent metadata reads are all best-effort) when it's empty.
    profile_dir = tmp_path / "seeded-profile"
    profile_dir.mkdir()
    last_profile_path = (
        fake_home / "Library" / "Application Support" / "online.curiositycat.shell" / "last-profile.json"
    )
    last_profile_path.write_text(json.dumps({"profile_dir": str(profile_dir)}))

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
                if not window_shown and WINDOW_SHOWN_MARKER in stdout_path.read_text(errors="replace"):
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
            assert WINDOW_SHOWN_MARKER in captured_stdout, (
                f"no {WINDOW_SHOWN_MARKER!r} within {LAUNCH_TIMEOUT_SECONDS}s — the app came up with a healthy "
                f"engine/watcher chain but never showed a window (APP-BUILD-4) — "
                f"stdout:\n{captured_stdout}\nstderr:\n{captured_stderr}"
            )

            print(f"[test_app_bundle] app pid={proc.pid} engine-listen pid={engine_listen_pid}")
            print(f"[test_app_bundle] stdout:\n{captured_stdout}")
            print(f"[test_app_bundle] stderr:\n{captured_stderr}")
        finally:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait(timeout=5)


CONFIRM_TRANSPORT_TIMEOUT_SECONDS = 5


def _read_line_with_timeout(stream, timeout_seconds):
    """Reads one newline-terminated line from `stream` (a raw byte pipe),
    or returns None if nothing arrives within `timeout_seconds`. Reads the
    underlying fd directly via `selectors` rather than a buffered file
    read, so this can't itself block past the deadline it's enforcing.
    """
    sel = selectors.DefaultSelector()
    sel.register(stream, selectors.EVENT_READ)
    try:
        deadline = time.monotonic() + timeout_seconds
        buf = b""
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not sel.select(timeout=remaining):
                return None
            chunk = os.read(stream.fileno(), 4096)
            if not chunk:
                return None
            buf += chunk
            if b"\n" in buf:
                return buf.split(b"\n", 1)[0]
    finally:
        sel.close()


def test_confirm_transport_round_trip_within_timeout(copied_bundle, tmp_path):
    """Drives the exact stdio transport the Guard Board's "Protect whole
    fleet" Confirm action uses — a line-delimited JSON `fleet` request to
    the built `ccat-engine` binary (sidecar.rs spawns this same binary with
    argv `serve`) — and asserts a response lands well inside the 5s bound
    now enforced in sidecar.rs. This is the transport a hung/unresponsive
    engine used to leave the Confirm button silently dead against.
    """
    engine_exe = copied_bundle / "Contents" / "MacOS" / "ccat-engine"
    assert engine_exe.exists()

    fake_home = tmp_path / "fake-home"
    fake_home.mkdir()
    project = tmp_path / "estate" / "myproject"
    project.mkdir(parents=True)

    env = {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "HOME": str(fake_home),
        "USER": os.environ.get("USER", "tester"),
        "CURIOSITY_CAT_HOME": str(tmp_path / "cc-home"),
    }

    proc = subprocess.Popen(
        [str(engine_exe), "serve"],
        cwd="/",
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
    )
    try:
        # sidecar.rs spawns ccat-engine once, eagerly, at app startup
        # (main.rs's setup()) — long before any window is even up for a
        # user to click Confirm on — and keeps that one process alive for
        # the rest of the session. A onefile PyInstaller binary's one-time
        # self-extraction happens during that startup spawn, not on every
        # call, so it's warmed up here with a generously-timed request
        # before the actually-timed one below, matching that real shape
        # rather than conflating cold-start unpack time with per-call
        # latency (what board.js's Confirm button is actually exposed to).
        proc.stdin.write((json.dumps({"id": 0, "method": "status", "params": {}}) + "\n").encode())
        proc.stdin.flush()
        warmup_line = _read_line_with_timeout(proc.stdout, LAUNCH_TIMEOUT_SECONDS)
        assert warmup_line is not None, f"ccat-engine never came up within {LAUNCH_TIMEOUT_SECONDS}s"

        request = {
            "id": 1,
            "method": "fleet",
            "params": {"level": "housecat", "observed": False, "targets": [str(project)]},
        }
        proc.stdin.write((json.dumps(request) + "\n").encode())
        proc.stdin.flush()

        line = _read_line_with_timeout(proc.stdout, CONFIRM_TRANSPORT_TIMEOUT_SECONDS)
        assert line is not None, (
            f"ccat-engine gave no response within {CONFIRM_TRANSPORT_TIMEOUT_SECONDS}s of an already-warm "
            "process — the exact silent dead-end APP-BUILD-6 traced the stuck Confirm modal to"
        )

        response = json.loads(line)
        assert response["id"] == 1
        assert "error" not in response, response.get("error")
        assert (project / ".claude" / "settings.json").exists()
    finally:
        proc.kill()
        proc.wait(timeout=5)
