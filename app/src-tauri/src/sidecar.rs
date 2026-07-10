//! Sidecar wiring for the `ccat-engine serve` process: spawns it once at
//! app startup and speaks the line-delimited JSON protocol from APP-1
//! (curiosity_cat/serve.py) over its stdin/stdout.
//!
//! APP-6 switched this from a dev-mode "look up `ccat-engine` on PATH"
//! `std::process::Command` to Tauri's `externalBin` sidecar mechanism
//! (tauri-plugin-shell): the PyInstaller-built binary
//! (app/packaging/build-sidecar.sh output, named per the target-triple
//! convention in `bundle.externalBin` / capabilities/default.json) is
//! bundled alongside the app and resolved by name rather than PATH, in
//! dev and in the signed/notarised build alike. The plugin's spawn API is
//! event-driven (an async `Receiver<CommandEvent>` fed by a background
//! reader task) rather than a blocking `BufReader`, so `call()` is async
//! and `SidecarState` uses an async-aware mutex that can be held across
//! an `.await`.

use serde_json::{json, Value};
use tauri::AppHandle;
use tauri::async_runtime::Mutex;
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

pub struct Sidecar {
    child: CommandChild,
    rx: tauri::async_runtime::Receiver<CommandEvent>,
    next_id: u64,
}

pub struct SidecarState(pub Mutex<Option<Sidecar>>);

impl Sidecar {
    fn spawn(app: &AppHandle) -> Result<Self, String> {
        let (rx, child) = app
            .shell()
            .sidecar("ccat-engine")
            .map_err(|e| format!("could not resolve ccat-engine sidecar: {e}"))?
            .args(["serve"])
            .spawn()
            .map_err(|e| format!("could not spawn ccat-engine sidecar: {e}"))?;

        Ok(Self { child, rx, next_id: 0 })
    }

    async fn call(&mut self, method: &str, params: Value) -> Result<Value, String> {
        self.next_id += 1;
        let request = json!({ "id": self.next_id, "method": method, "params": params });
        let mut line = serde_json::to_string(&request).map_err(|e| e.to_string())?;
        line.push('\n');

        self.child
            .write(line.as_bytes())
            .map_err(|e| format!("failed writing to ccat-engine stdin: {e}"))?;

        // ccat-engine writes exactly one response line per request, in
        // order (serve.py's serve_forever loop), so the first Stdout event
        // after our write is always this call's response — stderr lines
        // (Python tracebacks, warnings) are logged and skipped rather than
        // treated as the answer.
        while let Some(event) = self.rx.recv().await {
            match event {
                CommandEvent::Stdout(bytes) => {
                    let text = String::from_utf8_lossy(&bytes);
                    let response: Value = serde_json::from_str(text.trim())
                        .map_err(|e| format!("malformed response from ccat-engine: {e}"))?;
                    if let Some(error) = response.get("error") {
                        return Err(error.as_str().unwrap_or("unknown ccat-engine error").to_string());
                    }
                    return Ok(response.get("result").cloned().unwrap_or(Value::Null));
                }
                CommandEvent::Stderr(bytes) => {
                    eprintln!("[ccat-engine] {}", String::from_utf8_lossy(&bytes).trim_end());
                }
                CommandEvent::Error(e) => return Err(format!("ccat-engine sidecar error: {e}")),
                CommandEvent::Terminated(payload) => {
                    return Err(format!("ccat-engine exited (code {:?})", payload.code));
                }
                _ => {}
            }
        }
        Err("ccat-engine closed its stdout (process exited)".to_string())
    }
}

/// Spawn the sidecar eagerly at app startup. Logs to stderr and leaves the
/// slot empty on failure, so callers see a clear error on the next
/// `sidecar_call` rather than a crash at launch, matching the fail-open
/// spirit of the rest of this codebase.
pub fn init(app: &AppHandle, state: &SidecarState) {
    match Sidecar::spawn(app) {
        Ok(sidecar) => {
            *tauri::async_runtime::block_on(state.0.lock()) = Some(sidecar);
        }
        Err(e) => {
            eprintln!("[curiosity-cat] {e}");
        }
    }
}

pub async fn call(app: &AppHandle, state: &SidecarState, method: &str, params: Value) -> Result<Value, String> {
    let mut guard = state.0.lock().await;
    match guard.as_mut() {
        Some(sidecar) => sidecar.call(method, params).await,
        None => {
            // Not running yet (e.g. startup spawn failed) — try once more
            // before giving up, in case the sidecar can now be found.
            match Sidecar::spawn(app) {
                Ok(mut sidecar) => {
                    let result = sidecar.call(method, params).await;
                    *guard = Some(sidecar);
                    result
                }
                Err(e) => Err(e),
            }
        }
    }
}
