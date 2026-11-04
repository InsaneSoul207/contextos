// ContextOS - Personal AI Memory Infrastructure
// Tauri 2 Desktop Application - Rust Backend

use serde::{Deserialize, Serialize};
use std::sync::Mutex;
use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    AppHandle, Manager, State,
};

/// Application state shared across commands
pub struct AppState {
    pub backend_url: Mutex<String>,
    pub api_key: Mutex<String>,
    pub backend_running: Mutex<bool>,
}

/// Response from the Python backend health check
#[derive(Debug, Serialize, Deserialize)]
pub struct HealthResponse {
    pub status: String,
    pub version: String,
}

/// Backend status information
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct BackendStatus {
    pub running: bool,
    pub url: String,
    pub version: Option<String>,
}

/// Check if the Python backend is running
#[tauri::command]
pub async fn check_backend_health(state: State<'_, AppState>) -> Result<BackendStatus, String> {
    let url = state.backend_url.lock().unwrap().clone();
    let health_url = format!("{}/health", url);

    match reqwest::get(&health_url).await {
        Ok(response) => {
            if response.status().is_success() {
                let health: HealthResponse = response
                    .json()
                    .await
                    .map_err(|e| format!("Failed to parse health response: {}", e))?;
                *state.backend_running.lock().unwrap() = true;
                Ok(BackendStatus {
                    running: true,
                    url,
                    version: Some(health.version),
                })
            } else {
                *state.backend_running.lock().unwrap() = false;
                Ok(BackendStatus {
                    running: false,
                    url,
                    version: None,
                })
            }
        }
        Err(_) => {
            *state.backend_running.lock().unwrap() = false;
            Ok(BackendStatus {
                running: false,
                url,
                version: None,
            })
        }
    }
}

/// Get the backend API URL
#[tauri::command]
pub fn get_backend_url(state: State<'_, AppState>) -> String {
    state.backend_url.lock().unwrap().clone()
}

/// Set the backend API URL
#[tauri::command]
pub fn set_backend_url(state: State<'_, AppState>, url: String) {
    *state.backend_url.lock().unwrap() = url;
}

/// Get the API key
#[tauri::command]
pub fn get_api_key(state: State<'_, AppState>) -> String {
    state.api_key.lock().unwrap().clone()
}

/// Set the API key
#[tauri::command]
pub fn set_api_key(state: State<'_, AppState>, key: String) {
    *state.api_key.lock().unwrap() = key;
}

/// Get the application data directory
#[tauri::command]
pub fn get_data_dir() -> Result<String, String> {
    let data_dir = dirs::data_local_dir()
        .ok_or("Could not determine data directory")?
        .join("ContextOS");
    std::fs::create_dir_all(&data_dir)
        .map_err(|e| format!("Failed to create data directory: {}", e))?;
    Ok(data_dir.to_string_lossy().to_string())
}

/// Open a file or folder in the system file explorer
#[tauri::command]
pub fn open_in_explorer(path: String) -> Result<(), String> {
    #[cfg(target_os = "windows")]
    {
        std::process::Command::new("explorer")
            .arg(&path)
            .spawn()
            .map_err(|e| format!("Failed to open explorer: {}", e))?;
    }
    #[cfg(target_os = "macos")]
    {
        std::process::Command::new("open")
            .arg(&path)
            .spawn()
            .map_err(|e| format!("Failed to open Finder: {}", e))?;
    }
    #[cfg(target_os = "linux")]
    {
        std::process::Command::new("xdg-open")
            .arg(&path)
            .spawn()
            .map_err(|e| format!("Failed to open file manager: {}", e))?;
    }
    Ok(())
}

/// Set up the system tray icon and menu
pub fn setup_tray(app: &AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    let show_item = MenuItem::with_id(app, "show", "Show ContextOS", true, None::<&str>)?;
    let pause_item = MenuItem::with_id(app, "pause", "Pause Indexing", true, None::<&str>)?;
    let quit_item = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;

    let menu = Menu::with_items(app, &[&show_item, &pause_item, &quit_item])?;

    let _tray = TrayIconBuilder::new()
        .menu(&menu)
        .tooltip("ContextOS — Personal AI Memory")
        .on_menu_event(move |app, event| match event.id.as_ref() {
            "show" => {
                if let Some(window) = app.get_webview_window("main") {
                    let _ = window.show();
                    let _ = window.set_focus();
                }
            }
            "pause" => {
                // TODO: Send pause signal to backend
                log::info!("Pause indexing requested from tray");
            }
            "quit" => {
                log::info!("Quit requested from tray");
                app.exit(0);
            }
            _ => {}
        })
        .on_tray_icon_event(|tray, event| {
            if let TrayIconEvent::Click {
                button: MouseButton::Left,
                button_state: MouseButtonState::Up,
                ..
            } = event
            {
                let app = tray.app_handle();
                if let Some(window) = app.get_webview_window("main") {
                    let _ = window.show();
                    let _ = window.set_focus();
                }
            }
        })
        .build(app)?;

    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    env_logger::init();

    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_autostart::init(
            tauri_plugin_autostart::MacosLauncher::LaunchAgent,
            Some(vec!["--minimized"]),
        ))
        .plugin(tauri_plugin_store::Builder::default().build())
        .manage(AppState {
            backend_url: Mutex::new("http://127.0.0.1:44480".to_string()),
            api_key: Mutex::new(String::new()),
            backend_running: Mutex::new(false),
        })
        .setup(|app| {
            let handle = app.handle().clone();
            setup_tray(&handle)?;

            // Minimize to tray on close instead of exiting
            let window = app.get_webview_window("main").unwrap();
            window.on_window_event(move |event| {
                if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                    api.prevent_close();
                    if let Some(win) = handle.get_webview_window("main") {
                        let _ = win.hide();
                    }
                }
            });

            log::info!("ContextOS desktop application started");
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            check_backend_health,
            get_backend_url,
            set_backend_url,
            get_api_key,
            set_api_key,
            get_data_dir,
            open_in_explorer,
        ])
        .run(tauri::generate_context!())
        .expect("Error while running ContextOS");
}
