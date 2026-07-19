//! Watcher process management — spawns the same bundled `ccat-engine`
//! sidecar binary `sidecar.rs` uses for `serve`, here with a `listen
//! --profile <dir>` argv (curiosity_cat/serve.py's `main()` dispatches
//! that straight to curiosity_cat/listen.py, the reference Watcher
//! listener), bound to the fixed Watcher port (127.0.0.1:8377). Resolved
//! by name via `tauri_plugin_shell`'s `ShellExt::sidecar()` — the same
//! externalBin mechanism as `serve`, so a release build has zero
//! dependence on a PATH install of the curiosity-cat Python package. The
//! app does not reimplement any of the listener's logic: Feed events, Meow
//! formatting (curiosity_cat/meow.py) and the approval gate
//! (curiosity_cat/gate.py) all live in one place, Python, and the Feed
//! window / approval dialog (app/src/js/feed.js, app/src/approval.html)
//! talk to this process directly over plain HTTP — this module only owns
//! the child process's lifecycle.

use std::sync::Mutex;
use tauri::AppHandle;
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

pub struct WatcherState(pub Mutex<Option<CommandChild>>);

fn spawn(app: &AppHandle, profile_dir: &str) -> Result<CommandChild, String> {
    let (mut rx, child) = app
        .shell()
        .sidecar("ccat-engine")
        .map_err(|e| format!("could not resolve ccat-engine sidecar: {e}"))?
        .args(["listen", "--profile", profile_dir])
        .spawn()
        .map_err(|e| format!("could not spawn ccat-engine sidecar: {e}"))?;

    // Nothing here talks request/response to this process (unlike
    // sidecar.rs's `call()`) — it just prints Meow-voice lines for a human
    // tailing logs, so this task only drains the event stream (forwarding
    // to this process's own stdout/stderr) rather than let the pipe fill
    // up and block the child.
    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(bytes) => {
                    print!("{}", String::from_utf8_lossy(&bytes));
                }
                CommandEvent::Stderr(bytes) => {
                    eprint!("[watcher] {}", String::from_utf8_lossy(&bytes));
                }
                _ => {}
            }
        }
    });

    Ok(child)
}

/// Stop whatever watcher is currently running (if any) and start a fresh
/// one bound to `profile_dir`. Always a full restart rather than a
/// "leave it running" no-op: a stale watcher still pointed at the
/// previous profile would queue close calls into the wrong Mouse Tray.
pub fn restart(app: &AppHandle, state: &WatcherState, profile_dir: &str) {
    let mut guard = state.0.lock().unwrap();
    if let Some(child) = guard.take() {
        let _ = child.kill();
    }
    match spawn(app, profile_dir) {
        Ok(child) => *guard = Some(child),
        Err(e) => eprintln!("[curiosity-cat] {e}"),
    }
}

impl Drop for WatcherState {
    fn drop(&mut self) {
        if let Ok(mut guard) = self.0.lock() {
            if let Some(child) = guard.take() {
                let _ = child.kill();
            }
        }
    }
}
