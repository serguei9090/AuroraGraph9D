"""
userTest/ingest_knowledge.py
============================
REFERENCE INGESTION SCRIPT — Every option explained.

This script demonstrates the main AuroraGraph usage patterns.
Copy & adapt it to your own project.

USAGE
-----
# Basic (uses .env settings):
    uv run python userTest/ingest_knowledge.py

# Override workers and device via CLI:
    uv run python userTest/ingest_knowledge.py --workers 8 --device cuda

# Skip triple (entity) extraction for maximum speed:
    uv run python userTest/ingest_knowledge.py --no-triples

Windows note: run `$env:PYTHONUTF8=1` in PowerShell before executing
to ensure emoji output doesn't crash the console.

INSTALLATION REFERENCE
----------------------
# --- From source (development) ---
    uv sync --extra kuzu --extra fastembed

# --- As a pip library ---
    pip install auragraph[fastembed]           # CPU (recommended)
    pip install auragraph[kuzu,fastembed]      # Kùzu + CPU embedding
    pip install auragraph[neo4j,fastembed]     # Neo4j + CPU embedding

# --- NVIDIA CUDA GPU embeddings ---
    # Step 1: install the cuda extra
    pip install auragraph[cuda]
    # Step 2: replace onnxruntime with the CUDA 12 build
    pip install onnxruntime-gpu \\
      --extra-index-url https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/onnxruntime-cuda-12/pypi/simple/
    # Then set in .env: AURA_DEVICE=cuda

# --- Apple Silicon (MPS) ---
    pip install auragraph[mps]
    # Then set in .env: AURA_DEVICE=mps

CONFIGURATION (via .env or environment variables)
-------------------------------------------------
    AURA_DB_PROVIDER = sqlite | kuzu | neo4j      (default: sqlite)
    AURA_DEVICE      = auto | cpu | cuda | mps    (default: auto)
    AURA_CONCURRENCY = <int>                       (default: 4, 0=all cores)
    AURA_MODEL       = <ollama model name>         (default: llama3.1:8b)
    KUZU_DB_PATH     = <path>                      (default: ./auragraph_graph)
    NEO4J_URI        = bolt://localhost:7687
    NEO4J_USER       = neo4j
    NEO4J_PASSWORD   = yourpassword
    FTS5_MATCH_LIMIT = 25                          (chunks returned per query)
"""

import argparse
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

# ── Path bootstrap ─────────────────────────────────────────────────────────────
# Allows running this script directly from the repo without `pip install`.
# This line is NOT needed when the package is installed via pip/uv.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# ── Imports ────────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv  # noqa: E402

    from auragraph import AuroraGraphEngine  # noqa: E402
    from auragraph.core.config import config  # noqa: E402

    # ── Database backend import ──────────────────────────────────────────────
    # Uncomment the backend you want to use.
    # The corresponding extra must be installed (see header).
    from auragraph.db.kuzu import KuzuDB  # noqa: E402
    from auragraph.ingestion.extractor import extract_triples  # noqa: E402
    from auragraph.ingestion.parsers import extract_chunks  # noqa: E402
    from auragraph.providers.embeddings.fastembed_provider import FastEmbedProvider  # noqa: E402
except ImportError as e:
    print(f"Error: {e}. Please ensure dependencies are installed (uv sync).")
    sys.exit(1)

# Load .env from the project root (two levels up from this file)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Thread-safety lock for concurrent DB writes
_db_lock = threading.Lock()


# ── DB Factory ─────────────────────────────────────────────────────────────────
def build_db(db_path: Path):
    """
    Create the database backend instance.

    Swap the return statement below to change backends:

        return SQLiteFTS5DB(str(db_path.with_suffix(".db")))
            → SQLite FTS5, no extras, stores in a single .db file.

        return KuzuDB(str(db_path))
            → Kùzu embedded graph. Stores in a folder. Requires [kuzu] extra.
            → Supports full Hybrid Search: BM25 + vector HNSW.

        return Neo4jDB(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            user=os.getenv("NEO4J_USER", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "password"),
        )
            → Neo4j enterprise cluster. Requires [neo4j] extra + running server.
    """
    return KuzuDB(str(db_path))


# ── Embedder Factory ───────────────────────────────────────────────────────────
def build_embedder(device_override: str | None = None):
    """
    Create the embedding provider.

    Options:

        FastEmbedProvider(device="auto")
            → Rust+ONNX. Best balance of speed and install size (~100 MB).
            → device="auto" picks CUDA → CPU. Requires [fastembed] or [cuda] extra.

        FastEmbedProvider(device="cpu")
            → Force CPU even if GPU is present.

        FastEmbedProvider(device="cuda")
            → NVIDIA GPU. Requires [cuda] extra + special onnxruntime-gpu wheel.
            → See INSTALLATION REFERENCE at the top of this file.

        FastEmbedProvider(device="mps")
            → Apple Silicon. Requires [mps] extra.

        LocalEmbeddingProvider(device="cuda")
            → PyTorch + sentence-transformers. Larger install (~2 GB).
            → Requires [embeddings] extra.
            >>> from auragraph.providers.embeddings.local import LocalEmbeddingProvider

        None
            → Disables vector search. Only FTS keyword search will run.
    """
    if device_override:
        os.environ["AURA_DEVICE"] = device_override
    return FastEmbedProvider()


# ── Single-file ingestion ──────────────────────────────────────────────────────
def ingest_file(file_path: Path, engine: AuroraGraphEngine, skip_triples: bool = False, force: bool = False) -> dict:
    """
    Parse, embed and store one file in the graph database.

    Returns a result dict with filename, size, duration and status.
    Thread-safe: DB writes are protected by _db_lock.
    """
    fname = file_path.name
    size_mb = file_path.stat().st_size / (1024 * 1024)
    start = time.perf_counter()

    with _db_lock:
        already_done = engine.db.is_ingested(fname)

        if already_done and force:
            print(f"  [Force]  {fname} (Removing existing records...)")
            engine.db.delete_document(fname)
            already_done = False

    if already_done:
        return {"filename": fname, "size_mb": size_mb, "duration": None, "status": "cached"}

    try:
        print(f"  [Parse]  {fname}  ({size_mb:.1f} MB)")
        chunks = extract_chunks(str(file_path))
        chunk_count = len(chunks)

        if chunk_count == 0:
            return {"filename": fname, "size_mb": size_mb, "duration": 0.0, "status": "empty"}

        # 1. Batch embedding — much faster than per-chunk calls
        print(f"  [Embed]  {fname}  — {chunk_count} chunks")
        texts = [c["content"] for c in chunks]
        embeddings = engine.embedder.embed_batch(texts) if engine.embedder else [None] * chunk_count

        # 2. Iterate chunks: extract triples + insert into DB
        print(f"  [Graph]  {fname}  — writing to DB")
        for i, chunk in enumerate(chunks):
            if i % 50 == 0 or chunk_count < 50:
                pct = int(100 * i / chunk_count)
                print(f"     {fname}: {i}/{chunk_count} chunks  [{pct}%]")

            triples = []
            if not skip_triples:
                try:
                    triples = extract_triples(chunk["content"])
                except Exception:
                    pass  # triple extraction is best-effort

            with _db_lock:
                engine.db.insert_document(
                    filename=chunk["filename"],
                    content=chunk["content"],
                    metadata=chunk["metadata"],
                    embedding=embeddings[i] if i < len(embeddings) else None,
                    triples=triples,
                )

        duration = time.perf_counter() - start
        return {"filename": fname, "size_mb": size_mb, "duration": duration, "status": "ok"}

    except Exception as e:
        duration = time.perf_counter() - start
        return {"filename": fname, "size_mb": size_mb, "duration": duration, "status": f"FAILED: {e}"}


# ── Markdown report builder ────────────────────────────────────────────────────
def build_report(results: list, workers: int, device: str, total_elapsed: float) -> str:
    run_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# AuroraGraph Ingestion Report\n",
        f"**Run at:** {run_at}  ",
        f"**Device:** `{device.upper()}`  ",
        f"**Workers:** `{workers}`  ",
        f"**Total elapsed:** `{total_elapsed:.2f}s`\n",
        "| Filename | Size (MB) | Time | Status |",
        "| :--- | ---: | ---: | :--- |",
    ]
    for r in results:
        dur = f"{r['duration']:.2f}s" if r["duration"] is not None else "—"
        lines.append(f"| {r['filename']} | {r['size_mb']:.2f} | {dur} | {r['status']} |")
    return "\n".join(lines) + "\n"


# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="AuroraGraph — Batch Knowledge Ingestion")
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of parallel workers. 0 = all CPU cores. Default: AURA_CONCURRENCY from .env (4).",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="Embedding device override: auto | cpu | cuda | mps. Default: AURA_DEVICE from .env.",
    )
    parser.add_argument(
        "--no-triples",
        action="store_true",
        help="Skip (Subject)-[Predicate]->(Object) triple extraction for maximum speed.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-ingest files even if they are already in the database.",
    )
    args = parser.parse_args()

    workers = args.workers if args.workers is not None else config.AURA_CONCURRENCY
    if workers == 0:
        workers = os.cpu_count() or 4

    # ── Folder layout ──────────────────────────────────────────────────────────
    # knowledge/  → put your PDF, TXT, or MD files here
    # report_time.md → performance report generated after each run
    knowledge_path = Path(__file__).resolve().parent / "knowledge"
    report_path = Path(__file__).resolve().parent / "report_time.md"
    db_path = Path(__file__).resolve().parent / "auragraph_graph"

    supported_exts = {".pdf", ".txt", ".md"}
    files = sorted(f for f in knowledge_path.iterdir() if f.suffix.lower() in supported_exts)
    if not files:
        print(f"No supported files found in: {knowledge_path}")
        print("Add .pdf / .txt / .md files and try again.")
        return

    # ── Build engine ───────────────────────────────────────────────────────────
    # You can also pass AURA_DB_PROVIDER=kuzu via .env and let the engine
    # auto-select the backend via `engine = AuroraGraphEngine()`.
    # Here we build explicitly so it's easy to read.
    print("Initializing AuroraGraph (Kuzu + FastEmbed)...")
    embedder = build_embedder(device_override=args.device)
    db = build_db(db_path)
    engine = AuroraGraphEngine(db=db, embedder=embedder)

    # Resolve actual device after embedder init
    actual_device = getattr(embedder, "device", config.AURA_DEVICE)

    print(f"Workers: {workers}  |  Device: {actual_device.upper()}  |  Triples: {not args.no_triples}")
    print(f"Source: {knowledge_path}\n")

    # ── Parallel ingestion ─────────────────────────────────────────────────────
    results = []
    overall_start = time.perf_counter()

    try:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_file = {
                executor.submit(ingest_file, f, engine, args.no_triples, args.force): f for f in files
            }
            for future in as_completed(future_to_file):
                res = future.result()
                results.append(res)
                dur = f"{res['duration']:.2f}s" if res["duration"] is not None else "cached"
                status_msg = f"({res['status']})" if res["status"] != "ok" else ""
                print(f"  DONE: {res['filename']} — {dur} {status_msg}")
    except KeyboardInterrupt:
        print("\nIngestion interrupted. Saving partial report...")

    total_elapsed = time.perf_counter() - overall_start
    results.sort(key=lambda r: r["filename"])
    report = build_report(results, workers, actual_device, total_elapsed)
    report_path.write_text(report, encoding="utf-8")

    ok = sum(1 for r in results if r["status"] == "ok")
    cached = sum(1 for r in results if r["status"] == "cached")
    print(f"\nDone: {ok} ingested, {cached} cached, total {total_elapsed:.2f}s")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
