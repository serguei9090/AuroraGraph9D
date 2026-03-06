use pyo3::prelude::*;
use std::collections::HashSet;

/// Metabolic filter: drop low-information, boilerplate, or tiny chunks.
#[pyfunction]
#[pyo3(signature = (text))]
fn is_valid_text(text: &str) -> bool {
    let t = text.trim();
    if t.len() < 50 {
        return false;
    }

    let words: Vec<&str> = t.split_whitespace().collect();
    if words.len() < 5 {
        return false;
    }

    // Check information density (entropy via unique words)
    let unique_words: HashSet<&str> = words.iter().cloned().collect();
    let entropy = unique_words.len() as f64 / words.len() as f64;

    // highly repetitive or very homogeneous
    if entropy < 0.2 {
        return false;
    }

    true
}

/// Recursively chunk text down to max_chars by headers, paragraphs, lines, then words.
#[pyfunction]
#[pyo3(signature = (text, max_chars=2000))]
fn chunk_text(text: &str, max_chars: usize) -> Vec<String> {
    if text.len() <= max_chars {
        let trimmed = text.trim();
        if trimmed.is_empty() {
            return vec![];
        } else {
            return vec![trimmed.to_string()];
        }
    }

    // Try Level 1: Markdown headers (poor man's split)
    let mut header_split: Vec<&str> = Vec::new();
    let mut last_idx = 0;

    // Iterate over the string looking for "\n#" or "\n## "
    for (i, _) in text.match_indices("\n#") {
        if i > last_idx {
            header_split.push(&text[last_idx..i]);
            last_idx = i;
        }
    }
    header_split.push(&text[last_idx..]);

    if header_split.len() > 1 {
        let mut chunks = Vec::new();
        for section in header_split {
            chunks.extend(chunk_text(section.trim(), max_chars));
        }
        return chunks;
    }

    // Try Level 2: Paragraphs
    let para_split: Vec<&str> = text.split("\n\n").collect();
    if para_split.len() > 1 {
        let mut chunks = Vec::new();
        for section in para_split {
            chunks.extend(chunk_text(section.trim(), max_chars));
        }
        return chunks;
    }

    // Try Level 3: Lines
    let line_split: Vec<&str> = text.split('\n').collect();
    if line_split.len() > 1 {
        let mut chunks = Vec::new();
        let mut curr_chunk = String::new();

        for line in line_split {
            if curr_chunk.len() + line.len() + 1 > max_chars && !curr_chunk.is_empty() {
                chunks.extend(chunk_text(curr_chunk.trim(), max_chars));
                curr_chunk = line.to_string() + "\n";
            } else {
                curr_chunk.push_str(line);
                curr_chunk.push('\n');
            }
        }
        if !curr_chunk.trim().is_empty() {
            chunks.extend(chunk_text(curr_chunk.trim(), max_chars));
        }
        return chunks;
    }

    // Try Level 4: Words
    let mut chunks = Vec::new();
    let words: Vec<&str> = text.split_whitespace().collect();
    let mut curr_chunk = String::new();

    for word in words {
        if curr_chunk.len() + word.len() + 1 > max_chars && !curr_chunk.is_empty() {
            chunks.push(curr_chunk.trim().to_string());
            curr_chunk = word.to_string() + " ";
        } else {
            curr_chunk.push_str(word);
            curr_chunk.push(' ');
        }
    }

    if !curr_chunk.trim().is_empty() {
        chunks.push(curr_chunk.trim().to_string());
    }

    chunks
}

/// A Python module implemented in Rust.
#[pymodule]
fn auragraph_core(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(is_valid_text, m)?)?;
    m.add_function(wrap_pyfunction!(chunk_text, m)?)?;
    Ok(())
}
