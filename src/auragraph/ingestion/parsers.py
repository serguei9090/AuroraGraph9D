import os

import fitz

try:
    from auragraph import auragraph_core
except ImportError:
    print("[!] Failed to import Rust `auragraph_core`. Please run `uv tool run maturin develop`.")
    raise


def _is_valid_text(text: str) -> bool:
    """Metabolic filter: drop low-information, boilerplate, or tiny chunks."""
    return auragraph_core.is_valid_text(text)


def _chunk_text(text: str, max_chars: int = 2000) -> list[str]:
    """Recursively chunk text down to max_chars."""
    return auragraph_core.chunk_text(text, max_chars)


def parse_pdf(filepath: str) -> list[dict]:
    """Returns a list of chunks from a PDF file."""
    chunks = []
    fname = os.path.basename(filepath)
    try:
        doc = fitz.open(filepath)
        for pnum, page in enumerate(doc):
            text = page.get_text().strip()
            page_chunks = _chunk_text(text, max_chars=2000)

            for i, c_text in enumerate(page_chunks):
                if _is_valid_text(c_text):
                    chunks.append(
                        {
                            "filename": fname,
                            "content": c_text,
                            "metadata": {"page": pnum + 1, "chunk_index": i},
                        }
                    )
    except Exception as e:
        print(f"[!] Library Error reading PDF {fname}: {e}")
    return chunks


def parse_text(filepath: str) -> list[dict]:
    """Returns a list of chunks from a plain text/markdown file."""
    chunks = []
    fname = os.path.basename(filepath)
    try:
        with open(filepath, encoding="utf-8") as tf:
            text = tf.read().strip()

        text_chunks = _chunk_text(text, max_chars=2000)

        for i, c_text in enumerate(text_chunks):
            if _is_valid_text(c_text):
                chunks.append(
                    {
                        "filename": fname,
                        "content": c_text,
                        "metadata": {"chunk_index": i},
                    }
                )
    except Exception as e:
        print(f"[!] Library Error reading Text {fname}: {e}")
    return chunks


def extract_chunks(filepath: str) -> list[dict]:
    """Router for file parsers based on extension."""
    if filepath.lower().endswith(".pdf"):
        return parse_pdf(filepath)
    elif filepath.lower().endswith((".txt", ".md")):
        return parse_text(filepath)
    return []
