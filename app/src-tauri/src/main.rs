// Prevents an extra console window on Windows in release builds — no-op on
// macOS, which is the only target for v1 (APP_SPEC.md Shell section).
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;
mod sidecar;
mod tray;
mod watcher;

use sidecar::SidecarState;
use std::sync::Mutex;
use tauri::Manager;
use watcher::WatcherState;

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .manage(SidecarState(tauri::async_runtime::Mutex::new(None)))
        .manage(WatcherState(Mutex::new(None)))
        .setup(|app| {
            let handle = app.handle().clone();
            sidecar::init(&handle, &app.state::<SidecarState>());
            tray::build(app)?;

            // Menu bar app: no Dock icon, no window until the tray is
            // clicked or first-run needs to greet the user.
            #[cfg(target_os = "macos")]
            app.set_activation_policy(tauri::ActivationPolicy::Accessory);

            // Created hidden, not lazily on tray click: the Feed's JS
            // (app/src/js/feed.js) is what polls the Watcher listener for
            // live events and pending approval-gate holds, and that has to
            // keep running whether or not the user has the Feed window
            // open — this is the app's one always-on background webview.
            let _ = tauri::WebviewWindowBuilder::new(
                &handle,
                "feed",
                tauri::WebviewUrl::App("feed.html".into()),
            )
            .title("Curiosity Cat")
            .inner_size(720.0, 560.0)
            .visible(false)
            .build();

            if let Ok(Some(profile_dir)) = commands::get_last_profile_dir(handle.clone()) {
                watcher::restart(&handle, &handle.state::<WatcherState>(), &profile_dir);
            }

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
            commands::get_profiles_dir,
            commands::open_window,
            commands::close_window,
            commands::open_approval_window,
            commands::is_first_run,
            commands::complete_first_run,
            commands::get_last_profile_dir,
            commands::set_last_profile_dir,
            commands::read_text_file,
            commands::get_settings,
            commands::save_settings,
            tray::set_tray_state,
        ])
        .run(tauri::generate_context!())
        .expect("error while running curiosity-cat");
}
