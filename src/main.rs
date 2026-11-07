#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use lernplatform_core::{calculate_leitner_weight, fnv1a_hash, similarity_percent};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

fn cleanup_temp_files(dir: &Path) {
    if let Ok(entries) = fs::read_dir(dir) {
        for entry in entries.flatten() {
            let p = entry.path();
            if let Some(name) = p.file_name().and_then(|n| n.to_str()) {
                if name.ends_with(".old") || name.ends_with(".tmp") {
                    let _ = fs::remove_file(&p);
                }
            }
        }
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.iter().any(|a| a == "--version" || a == "-V") {
        println!("Lernplatform v2.5.0 (Native Rust Core & Launcher)");
        return;
    }
    if args.iter().any(|a| a == "--verify") {
        let sim = similarity_percent("entrepreneurship", "enterpreneurship");
        let w = calculate_leitner_weight(3, 1, 2);
        let h = fnv1a_hash(b"Lernplatform-Rust-Core");
        println!(
            "Lernplatform Rust Core OK (Similarity: {}%, Weight: {:.3}, FNV-1a: {:016x})",
            sim, w, h
        );
        return;
    }

    let exe_path = std::env::current_exe().unwrap_or_else(|_| PathBuf::from("."));
    let base_dir = exe_path.parent().unwrap_or_else(|| Path::new(".")).to_path_buf();
    cleanup_temp_files(&base_dir);

    let main_py = base_dir.join("main.py");
    if main_py.is_file() {
        let _ = Command::new("pythonw")
            .arg(&main_py)
            .current_dir(&base_dir)
            .spawn()
            .or_else(|_| {
                Command::new("python")
                    .arg(&main_py)
                    .current_dir(&base_dir)
                    .spawn()
            });
    }
}
