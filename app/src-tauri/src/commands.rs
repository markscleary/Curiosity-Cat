use crate::sidecar::SidecarState;
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
pub fn sidecar_call(
    app: AppHandle,
    method: String,
    params: Option<Value>,
) -> Result<Value, String> {
    let state = app.state::<SidecarState>();
    crate::sidecar::call(&state, &method, params.unwrap_or(Value::Object(Default::default())))
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

/// Read back a file the sidecar just wrote (PROFILE.md, clean-bill.md, ...)
/// so the shell can render it. `ccat-engine` already has full local
/// filesystem access to do its job (compiling profiles, writing clean
/// bills) — this just lets the UI display what it produced, it does not
/// widen the app's actual filesystem trust boundary.
#[tauri::command]
pub fn read_text_file(path: String) -> Result<String, String> {
    fs::read_to_string(path).map_err(|e| e.to_string())
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

#[tauri::command]
pub fn set_last_profile_dir(app: AppHandle, profile_dir: String) -> Result<(), String> {
    let path = last_profile_path(&app)?;
    let contents = serde_json::json!({ "profile_dir": profile_dir }).to_string();
    fs::write(path, contents).map_err(|e| e.to_string())
}
