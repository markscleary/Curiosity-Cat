//! Tray icon state machine — APP_SPEC.md Shell section: "tray icon = cat
//! state machine (asleep=housecat quiet; ears-up=activity; hackles=close
//! call; mouse=tripwire/alarm)". Art is placeholder monochrome glyphs
//! (tray-icons/*.svg source, *.png runtime) for a later artist pass; the
//! state machine plumbing (set_tray_state) is real and is what APP-4's
//! live Watcher feed will drive.

use std::collections::HashMap;
use tauri::image::Image;
use tauri::menu::{Menu, MenuItem, PredefinedMenuItem};
use tauri::tray::TrayIconBuilder;
use tauri::{App, AppHandle, Manager};

pub const STATE_ASLEEP: &str = "asleep";
pub const STATE_EARS_UP: &str = "ears-up";
pub const STATE_HACKLES: &str = "hackles";
pub const STATE_MOUSE: &str = "mouse";

pub struct TrayIcons(pub HashMap<&'static str, Image<'static>>);

fn load_icons() -> TrayIcons {
    let mut icons = HashMap::new();
    icons.insert(
        STATE_ASLEEP,
        Image::from_bytes(include_bytes!("../tray-icons/asleep.png")).expect("decode asleep.png"),
    );
    icons.insert(
        STATE_EARS_UP,
        Image::from_bytes(include_bytes!("../tray-icons/ears-up.png")).expect("decode ears-up.png"),
    );
    icons.insert(
        STATE_HACKLES,
        Image::from_bytes(include_bytes!("../tray-icons/hackles.png")).expect("decode hackles.png"),
    );
    icons.insert(
        STATE_MOUSE,
        Image::from_bytes(include_bytes!("../tray-icons/mouse.png")).expect("decode mouse.png"),
    );
    TrayIcons(icons)
}

pub fn build(app: &App) -> tauri::Result<()> {
    let icons = load_icons();
    let asleep = icons.0.get(STATE_ASLEEP).expect("asleep icon loaded").clone();

    // Guard Board leads the menu — it's the app's landing view (APP-G1):
    // opening the app should answer what/from-what/since-when before
    // anything else, not default to the Slider.
    let open_board = MenuItem::with_id(app, "open_board", "Guard Board", true, None::<&str>)?;
    let open_slider = MenuItem::with_id(app, "open_slider", "Open Slider", true, None::<&str>)?;
    let open_feed = MenuItem::with_id(app, "open_feed", "Feed", true, None::<&str>)?;
    let open_purr = MenuItem::with_id(app, "open_purr", "This Week's Purr", true, None::<&str>)?;
    let quit = PredefinedMenuItem::quit(app, Some("Quit"))?;
    let menu = Menu::with_items(app, &[&open_board, &open_slider, &open_feed, &open_purr, &quit])?;

    let _tray = TrayIconBuilder::with_id("main")
        .icon(asleep)
        .icon_as_template(true)
        .menu(&menu)
        .show_menu_on_left_click(true)
        .on_menu_event(|app, event| match event.id.as_ref() {
            "open_slider" => crate::commands::show_window(app, "slider", "slider.html"),
            "open_feed" => crate::commands::show_window(app, "feed", "feed.html"),
            "open_board" => crate::commands::show_window(app, "board", "board.html"),
            "open_purr" => crate::commands::show_window(app, "purr", "purr.html"),
            _ => {}
        })
        .build(app)?;

    app.manage(icons);
    Ok(())
}

/// Switch the tray glyph to `state` (one of the STATE_* constants). Exposed
/// as a Tauri command so the Feed window (APP-4) can drive it live off
/// Watcher events; unknown state names are ignored rather than panicking,
/// since a stale frontend build must never crash the shell.
#[tauri::command]
pub fn set_tray_state(app: AppHandle, state: String) -> Result<(), String> {
    let icons = app.state::<TrayIcons>();
    let image = icons
        .0
        .get(state.as_str())
        .ok_or_else(|| format!("unknown tray state: {state}"))?
        .clone();
    let tray = app
        .tray_by_id("main")
        .ok_or_else(|| "tray icon not found".to_string())?;
    tray.set_icon(Some(image)).map_err(|e| e.to_string())
}
