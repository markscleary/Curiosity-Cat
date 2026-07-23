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
use std::time::Duration;
use tauri::AppHandle;
use tauri::async_runtime::Mutex;
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

/// A hung or unresponsive ccat-engine used to have no bound at all: `call()`
/// awaited its stdout receiver forever, which meant a confirm action (Guard
/// Board's Protect/Undo whole fleet) could look "stuck" indefinitely with no
/// error and no button ever re-enabling (APP-BUILD-6). Every request now
/// gives up after this long and reports a clear timeout error instead.
const CALL_TIMEOUT: Duration = Duration::from_secs(5);

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
        let id = self.next_id;
        let request = json!({ "id": id, "method": method, "params": params });
        let mut line = serde_json::to_string(&request).map_err(|e| e.to_string())?;
        line.push('\n');

        self.child
            .write(line.as_bytes())
            .map_err(|e| format!("failed writing to ccat-engine stdin: {e}"))?;

        match tokio::time::timeout(CALL_TIMEOUT, read_response(&mut self.rx, id)).await {
            Ok(result) => result,
            Err(_) => Err(format!(
                "ccat-engine did not respond to \"{method}\" within {}s",
                CALL_TIMEOUT.as_secs()
            )),
        }
    }
}

/// Reads Stdout events until one parses as the response to `expected_id`,
/// logging Stderr (Python tracebacks, warnings) rather than treating it as
/// the answer. A response left over from a call that already timed out
/// carries a stale id and is skipped here rather than handed to whichever
/// later call happens to be waiting next — see `parse_response`.
async fn read_response(
    rx: &mut tauri::async_runtime::Receiver<CommandEvent>,
    expected_id: u64,
) -> Result<Value, String> {
    while let Some(event) = rx.recv().await {
        match event {
            CommandEvent::Stdout(bytes) => match parse_response(&bytes, expected_id) {
                Some(result) => return result,
                None => continue,
            },
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

/// Parses one stdout line as a `{"id": ..., "result"|"error": ...}` response
/// (serve.py's wire format). Returns `None` when the line's id doesn't match
/// `expected_id` — a stale response for an already-timed-out call — so the
/// caller keeps waiting instead of returning the wrong request's answer.
fn parse_response(bytes: &[u8], expected_id: u64) -> Option<Result<Value, String>> {
    let text = String::from_utf8_lossy(bytes);
    let response: Value = match serde_json::from_str(text.trim()) {
        Ok(v) => v,
        Err(e) => return Some(Err(format!("malformed response from ccat-engine: {e}"))),
    };
    if response.get("id").and_then(Value::as_u64) != Some(expected_id) {
        return None;
    }
    if let Some(error) = response.get("error") {
        return Some(Err(error.as_str().unwrap_or("unknown ccat-engine error").to_string()));
    }
    Some(Ok(response.get("result").cloned().unwrap_or(Value::Null)))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_response_matching_id_returns_the_result() {
        let result = parse_response(br#"{"id":1,"result":{"ok":true}}"#, 1).expect("should match");
        assert_eq!(result.unwrap(), json!({"ok": true}));
    }

    #[test]
    fn parse_response_matching_id_returns_the_error() {
        let result = parse_response(br#"{"id":2,"error":"boom"}"#, 2).expect("should match");
        assert_eq!(result.unwrap_err(), "boom");
    }

    #[test]
    fn parse_response_missing_result_defaults_to_null() {
        let result = parse_response(br#"{"id":3}"#, 3).expect("should match");
        assert_eq!(result.unwrap(), Value::Null);
    }

    #[test]
    fn parse_response_stale_id_is_skipped_not_misdelivered() {
        // A response for a call that already timed out (APP-BUILD-6) must
        // never be handed to a later call waiting on a different id.
        assert!(parse_response(br#"{"id":1,"result":{"ok":true}}"#, 2).is_none());
    }

    #[test]
    fn parse_response_malformed_json_is_an_error_regardless_of_id() {
        let result = parse_response(b"not json", 1).expect("malformed is always Some");
        assert!(result.unwrap_err().contains("malformed response"));
    }

    #[tokio::test]
    async fn read_response_times_out_when_nothing_ever_arrives() {
        let (_tx, mut rx) = tokio::sync::mpsc::channel::<CommandEvent>(1);
        let outcome = tokio::time::timeout(Duration::from_millis(50), read_response(&mut rx, 1)).await;
        assert!(outcome.is_err(), "expected the outer timeout to fire, got {outcome:?}");
    }

    #[tokio::test]
    async fn read_response_skips_a_stale_response_and_returns_the_matching_one() {
        let (tx, mut rx) = tokio::sync::mpsc::channel::<CommandEvent>(4);
        tx.send(CommandEvent::Stdout(br#"{"id":1,"result":"stale"}"#.to_vec()))
            .await
            .unwrap();
        tx.send(CommandEvent::Stdout(br#"{"id":2,"result":"fresh"}"#.to_vec()))
            .await
            .unwrap();
        let result = read_response(&mut rx, 2).await.unwrap();
        assert_eq!(result, json!("fresh"));
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
