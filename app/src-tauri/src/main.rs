// Prevents an extra console window on Windows in release builds — no-op on
// macOS, which is the only target for v1 (APP_SPEC.md Shell section).
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;
mod sidecar;
mod tray;

use sidecar::SidecarState;
use std::sync::Mutex;
use tauri::Manager;

fn main() {
    tauri::Builder::default()
        .manage(SidecarState(Mutex::new(None)))
        .setup(|app| {
            sidecar::init(&app.state::<SidecarState>());
            tray::build(app)?;

            // Menu bar app: no Dock icon, no window until the tray is
            // clicked or first-run needs to greet the user.
            #[cfg(target_os = "macos")]
            app.set_activation_policy(tauri::ActivationPolicy::Accessory);

            let handle = app.handle().clone();
            if commands::is_first_run(handle.clone()).unwrap_or(true) {
                commands::open_window(
                    handle,
                    "firstrun".to_string(),
                    "firstrun/choose.html".to_string(),
                );
            }

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::sidecar_call,
            commands::open_window,
            commands::is_first_run,
            commands::complete_first_run,
            commands::get_last_profile_dir,
            commands::set_last_profile_dir,
            commands::read_text_file,
            tray::set_tray_state,
        ])
        .run(tauri::generate_context!())
        .expect("error while running curiosity-cat");
}
