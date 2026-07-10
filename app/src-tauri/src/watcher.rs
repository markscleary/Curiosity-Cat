//! Watcher process management — spawns `curiosity-cat listen --profile
//! <dir>` (curiosity_cat/listen.py, the same reference listener APP-2
//! ships as a CLI command) as its own child process, bound to the fixed
//! Watcher port (127.0.0.1:8377). The app does not reimplement any of the
//! listener's logic: Feed events, Meow formatting (curiosity_cat/meow.py)
//! and the approval gate (curiosity_cat/gate.py) all live in one place,
//! Python, and the Feed window / approval dialog (app/src/js/feed.js,
//! app/src/approval.html) talk to this process directly over plain HTTP —
//! this module only owns the child process's lifecycle, the same
//! dev-mode-spawns-off-PATH approach `sidecar.rs` uses for `ccat-engine`.

use std::process::{Child, Command, Stdio};
use std::sync::Mutex;

pub struct WatcherState(pub Mutex<Option<Child>>);

fn spawn(profile_dir: &str) -> std::io::Result<Child> {
    Command::new("curiosity-cat")
        .args(["listen", "--profile", profile_dir])
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::inherit())
        .spawn()
}

/// Stop whatever watcher is currently running (if any) and start a fresh
/// one bound to `profile_dir`. Always a full restart rather than a
/// "leave it running" no-op: a stale watcher still pointed at the
/// previous profile would queue close calls into the wrong Mouse Tray.
pub fn restart(state: &WatcherState, profile_dir: &str) {
    let mut guard = state.0.lock().unwrap();
    if let Some(mut child) = guard.take() {
        let _ = child.kill();
        let _ = child.wait();
    }
    match spawn(profile_dir) {
        Ok(child) => *guard = Some(child),
        Err(e) => {
            eprintln!("[curiosity-cat] could not start watcher listener: {e}");
            eprintln!("[curiosity-cat] is the curiosity-cat package installed (`pip install -e .`)?");
        }
    }
}

impl Drop for WatcherState {
    fn drop(&mut self) {
        if let Ok(mut guard) = self.0.lock() {
            if let Some(mut child) = guard.take() {
                let _ = child.kill();
            }
        }
    }
}
