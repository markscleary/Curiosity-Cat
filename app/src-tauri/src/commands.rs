use crate::sidecar::SidecarState;
use crate::watcher::WatcherState;
use serde_json::Value;
use std::fs;
use tauri::{AppHandle, Manager, WebviewUrl, WebviewWindowBuilder};

const FIRST_RUN_MARKER: &str = "first-run-complete";
const LAST_PROFILE_FILE: &str = "last-profile.json";

/// Generic bridge to the sidecar's line-delimited JSON protocol (APP-1,
/// curiosity_cat/serve.py METHODS): `invoke('sidecar_call', {method, params})`
/// from the frontend maps directly onto one `{"method": ..., "params": ...}`
/// request. No method allow-list here — the sidecar itself validates method
/// names (serve.py DISPATCH) and returns a normal `{"error": ...}` response
/// for an unknown one, so this stays a thin, protocol-shaped passthrough.
#[tauri::command]
pub async fn sidecar_call(
    app: AppHandle,
    method: String,
    params: Option<Value>,
) -> Result<Value, String> {
    let state = app.state::<SidecarState>();
    crate::sidecar::call(&app, &state, &method, params.unwrap_or(Value::Object(Default::default()))).await
}

/// Show a window for `label`/`url`, creating it on first use and just
/// focusing it on subsequent calls (tray menu clicks, first-run
/// navigation) rather than stacking duplicate windows.
pub fn show_window(app: &AppHandle, label: &str, url: &str) {
    if let Some(window) = app.get_webview_window(label) {
        let _ = window.show();
        let _ = window.set_focus();
        return;
    }
    let _ = WebviewWindowBuilder::new(app, label, WebviewUrl::App(url.into()))
        .title("Curiosity Cat")
        .inner_size(720.0, 560.0)
        .build();
}

#[tauri::command]
pub fn open_window(app: AppHandle, label: String, url: String) {
    show_window(&app, &label, &url);
}

#[tauri::command]
pub fn close_window(app: AppHandle, label: String) -> Result<(), String> {
    if let Some(window) = app.get_webview_window(&label) {
        window.close().map_err(|e| e.to_string())?;
    }
    Ok(())
}

/// Opens the approval-gate dialog for one held event (APP_SPEC.md Watcher
/// section: "app surfaces one-sentence Meow-spec prompt") — a small,
/// always-on-top window distinct from `show_window`'s regular-sized ones,
/// since this is meant to interrupt and be answered quickly: the
/// PreToolUse hook waiting on the other end has its own timeout (see
/// curiosity_cat/gate.py). `entry_id` is the Watcher listener's own
/// `/event/hold/pending` id; approval.html fetches that endpoint itself to
/// render the Meow sentence, rather than this command copying it through —
/// one less place for the text to drift out of sync with the listener's
/// own record of it. A second call for the same still-open entry_id is a
/// no-op rather than stacking a duplicate window.
#[tauri::command]
pub fn open_approval_window(app: AppHandle, entry_id: i64) -> Result<(), String> {
    let label = format!("approval-{entry_id}");
    if app.get_webview_window(&label).is_some() {
        return Ok(());
    }
    let url = format!("approval.html?entryId={entry_id}&label={label}");
    WebviewWindowBuilder::new(&app, &label, WebviewUrl::App(url.into()))
        .title("Curiosity Cat — Approval needed")
        .inner_size(420.0, 260.0)
        .resizable(false)
        .always_on_top(true)
        .center()
        .build()
        .map_err(|e| e.to_string())?;
    Ok(())
}

/// Read back a file the sidecar just wrote (PROFILE.md, clean-bill.md, ...)
/// so the shell can render it. `ccat-engine` already has full local
/// filesystem access to do its job (compiling profiles, writing clean
/// bills) — this just lets the UI display what it produced, it does not
/// widen the app's actual filesystem trust boundary.
#[tauri::command]
pub fn read_text_file(path: String) -> Result<String, String> {
    fs::read_to_string(path).map_err(|e| e.to_string())
}

/// Where this installed app keeps compiled profiles — passed explicitly to
/// the sidecar's `compile` call (see sidecar-client.js) rather than letting
/// ccat-engine fall back to its own cwd-derived default. A Finder launch
/// gives the sidecar cwd "/" (read-only), which is exactly the bug this
/// works around: the app always knows and states its own writable data
/// directory, the same one `marker_path`/`last_profile_path` already use.
fn profiles_dir_path(app: &AppHandle) -> Result<std::path::PathBuf, String> {
    let dir = app
        .path()
        .app_data_dir()
        .map_err(|e| format!("could not resolve app data dir: {e}"))?
        .join("profiles");
    fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    Ok(dir)
}

#[tauri::command]
pub fn get_profiles_dir(app: AppHandle) -> Result<String, String> {
    Ok(profiles_dir_path(&app)?.to_string_lossy().to_string())
}

fn marker_path(app: &AppHandle) -> Result<std::path::PathBuf, String> {
    let dir = app
        .path()
        .app_data_dir()
        .map_err(|e| format!("could not resolve app data dir: {e}"))?;
    fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    Ok(dir.join(FIRST_RUN_MARKER))
}

#[tauri::command]
pub fn is_first_run(app: AppHandle) -> Result<bool, String> {
    Ok(!marker_path(&app)?.exists())
}

/// Called from the Clean Bill screen once the first-run journey completes,
/// so the tray click path opens straight to the Slider from then on.
#[tauri::command]
pub fn complete_first_run(app: AppHandle) -> Result<(), String> {
    fs::write(marker_path(&app)?, b"").map_err(|e| e.to_string())
}

fn last_profile_path(app: &AppHandle) -> Result<std::path::PathBuf, String> {
    let dir = app
        .path()
        .app_data_dir()
        .map_err(|e| format!("could not resolve app data dir: {e}"))?;
    fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    Ok(dir.join(LAST_PROFILE_FILE))
}

/// The most recently compiled profile's directory, persisted to disk (not
/// window-local storage) so the Slider window, the first-run flow, and the
/// Feed window stub — three separate webviews — all agree on which
/// profile's Mouse Tray to read. `None` until the first successful compile.
#[tauri::command]
pub fn get_last_profile_dir(app: AppHandle) -> Result<Option<String>, String> {
    let path = last_profile_path(&app)?;
    if !path.exists() {
        return Ok(None);
    }
    let raw = fs::read_to_string(&path).map_err(|e| e.to_string())?;
    let value: Value = serde_json::from_str(&raw).map_err(|e| e.to_string())?;
    Ok(value.get("profile_dir").and_then(|v| v.as_str()).map(String::from))
}

/// Persists the active profile *and* restarts the Watcher listener to
/// point at it — a compile without a live watcher behind it would mean
/// Watcher hook events (and the approval gate) had nowhere to reach, so
/// this is the one place that keeps "the profile the Feed reads" and "the
/// profile the watcher is bound to" from drifting apart.
#[tauri::command]
pub fn set_last_profile_dir(app: AppHandle, profile_dir: String) -> Result<(), String> {
    let path = last_profile_path(&app)?;
    let contents = serde_json::json!({ "profile_dir": profile_dir }).to_string();
    fs::write(path, contents).map_err(|e| e.to_string())?;
    crate::watcher::restart(&app.state::<WatcherState>(), &profile_dir);
    Ok(())
}
