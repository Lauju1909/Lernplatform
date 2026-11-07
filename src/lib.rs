//! Native Rust Core Engine (`lernplatform_core.dll`) for Lernplatform.
//! Provides high-speed Unicode Levenshtein distance, fuzzy vocabulary matching,
//! Leitner spaced-repetition weighting, and FNV-1a file integrity hashing.

use std::ffi::CStr;
use std::fs;
use std::os::raw::c_char;
use std::path::Path;

/// Compute Unicode-aware Levenshtein edit distance between two strings (case-insensitive).
pub fn levenshtein_distance(a: &str, b: &str) -> u32 {
    let a_chars: Vec<char> = a.trim().to_lowercase().chars().collect();
    let b_chars: Vec<char> = b.trim().to_lowercase().chars().collect();
    let m = a_chars.len();
    let n = b_chars.len();

    if m == 0 {
        return n as u32;
    }
    if n == 0 {
        return m as u32;
    }

    let mut prev: Vec<usize> = (0..=n).collect();
    let mut curr: Vec<usize> = vec![0; n + 1];

    for i in 1..=m {
        curr[0] = i;
        for j in 1..=n {
            let cost = if a_chars[i - 1] == b_chars[j - 1] {
                0
            } else {
                1
            };
            curr[j] = (prev[j] + 1).min(curr[j - 1] + 1).min(prev[j - 1] + cost);
        }
        std::mem::swap(&mut prev, &mut curr);
    }

    prev[n] as u32
}

/// Compute similarity percentage (0..=100) between user answer and target vocabulary.
pub fn similarity_percent(a: &str, b: &str) -> u32 {
    let a_len = a.trim().chars().count();
    let b_len = b.trim().chars().count();
    let max_len = a_len.max(b_len);
    if max_len == 0 {
        return 100;
    }
    let dist = levenshtein_distance(a, b) as usize;
    let matched = max_len.saturating_sub(dist);
    ((matched * 100) / max_len) as u32
}

/// Compute Leitner spaced-repetition selection weight in Rust.
pub fn calculate_leitner_weight(correct: u32, wrong: u32, streak: u32) -> f64 {
    let base = 1.0 + (wrong as f64 * 2.5);
    let reduction = 1.0 + (correct as f64 * 0.45) + (streak as f64 * 0.8);
    (base / reduction).max(0.05)
}

/// Compute 64-bit FNV-1a integrity hash of a byte slice.
pub fn fnv1a_hash(bytes: &[u8]) -> u64 {
    let mut hash: u64 = 0xcbf29ce484222325;
    for &b in bytes {
        hash ^= b as u64;
        hash = hash.wrapping_mul(0x100000001b3);
    }
    hash
}

#[no_mangle]
pub extern "C" fn rust_lp_levenshtein(a_ptr: *const c_char, b_ptr: *const c_char) -> u32 {
    if a_ptr.is_null() || b_ptr.is_null() {
        return u32::MAX;
    }
    let a = unsafe { CStr::from_ptr(a_ptr) }.to_string_lossy();
    let b = unsafe { CStr::from_ptr(b_ptr) }.to_string_lossy();
    levenshtein_distance(&a, &b)
}

#[no_mangle]
pub extern "C" fn rust_lp_similarity_percent(a_ptr: *const c_char, b_ptr: *const c_char) -> u32 {
    if a_ptr.is_null() || b_ptr.is_null() {
        return 0;
    }
    let a = unsafe { CStr::from_ptr(a_ptr) }.to_string_lossy();
    let b = unsafe { CStr::from_ptr(b_ptr) }.to_string_lossy();
    similarity_percent(&a, &b)
}

#[no_mangle]
pub extern "C" fn rust_lp_calc_weight(correct: u32, wrong: u32, streak: u32) -> f64 {
    calculate_leitner_weight(correct, wrong, streak)
}

#[no_mangle]
pub extern "C" fn rust_lp_file_hash(path_ptr: *const c_char) -> u64 {
    if path_ptr.is_null() {
        return 0;
    }
    let path_str = match unsafe { CStr::from_ptr(path_ptr) }.to_str() {
        Ok(s) => s,
        Err(_) => return 0,
    };
    match fs::read(Path::new(path_str)) {
        Ok(bytes) => fnv1a_hash(&bytes),
        Err(_) => 0,
    }
}
