//! Sidecar wiring for the `ccat-engine serve` process: spawns it once at
//! app startup and speaks the line-delimited JSON protocol from APP-1
//! (curiosity_cat/serve.py) over its stdin/stdout.
//!
//! Dev mode spawns the `ccat-engine` console-script installed on PATH (see
//! app/README.md for the pip install step). The PyInstaller-built sidecar
//! binary (packaged via Tauri's `externalBin`) is a later, APP-6 step —
//! this module's call surface does not change when that lands, only how
//! the child process is located.

use serde_json::{json, Value};
use std::io::{BufRead, BufReader, Write};
use std::process::{Child, ChildStdin, Command, Stdio};
use std::sync::Mutex;

pub struct Sidecar {
    child: Child,
    stdin: ChildStdin,
    stdout: BufReader<std::process::ChildStdout>,
    next_id: u64,
}

pub struct SidecarState(pub Mutex<Option<Sidecar>>);

impl Sidecar {
    fn spawn() -> std::io::Result<Self> {
        let mut child = Command::new("ccat-engine")
            .arg("serve")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::inherit())
            .spawn()?;

        let stdin = child.stdin.take().expect("piped stdin");
        let stdout = BufReader::new(child.stdout.take().expect("piped stdout"));

        Ok(Self {
            child,
            stdin,
            stdout,
            next_id: 0,
        })
    }

    fn call(&mut self, method: &str, params: Value) -> Result<Value, String> {
        self.next_id += 1;
        let request = json!({ "id": self.next_id, "method": method, "params": params });
        let mut line = serde_json::to_string(&request).map_err(|e| e.to_string())?;
        line.push('\n');

        self.stdin
            .write_all(line.as_bytes())
            .map_err(|e| format!("failed writing to ccat-engine stdin: {e}"))?;
        self.stdin
            .flush()
            .map_err(|e| format!("failed flushing ccat-engine stdin: {e}"))?;

        let mut response_line = String::new();
        let n = self
            .stdout
            .read_line(&mut response_line)
            .map_err(|e| format!("failed reading ccat-engine stdout: {e}"))?;
        if n == 0 {
            return Err("ccat-engine closed its stdout (process exited)".to_string());
        }

        let response: Value = serde_json::from_str(response_line.trim())
            .map_err(|e| format!("malformed response from ccat-engine: {e}"))?;

        if let Some(error) = response.get("error") {
            return Err(error.as_str().unwrap_or("unknown ccat-engine error").to_string());
        }
        Ok(response.get("result").cloned().unwrap_or(Value::Null))
    }
}

impl Drop for Sidecar {
    fn drop(&mut self) {
        let _ = self.child.kill();
    }
}

/// Spawn the sidecar eagerly at app startup. Logs to stderr and leaves the
/// slot empty on failure (e.g. `ccat-engine` not on PATH in dev) — callers
/// see a clear error on the next `sidecar_call` rather than a crash at
/// launch, matching the fail-open spirit of the rest of this codebase.
pub fn init(state: &SidecarState) {
    match Sidecar::spawn() {
        Ok(sidecar) => {
            *state.0.lock().unwrap() = Some(sidecar);
        }
        Err(e) => {
            eprintln!("[curiosity-cat] could not start ccat-engine serve: {e}");
            eprintln!("[curiosity-cat] is the curiosity-cat package installed (`pip install -e .`)?");
        }
    }
}

pub fn call(state: &SidecarState, method: &str, params: Value) -> Result<Value, String> {
    let mut guard = state.0.lock().unwrap();
    match guard.as_mut() {
        Some(sidecar) => sidecar.call(method, params),
        None => {
            // Not running yet (e.g. startup spawn failed) — try once more
            // before giving up, in case ccat-engine has since been
            // installed and the user retried from the UI.
            match Sidecar::spawn() {
                Ok(mut sidecar) => {
                    let result = sidecar.call(method, params);
                    *guard = Some(sidecar);
                    result
                }
                Err(e) => Err(format!("ccat-engine is not running: {e}")),
            }
        }
    }
}
