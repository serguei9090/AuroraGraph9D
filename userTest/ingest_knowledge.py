"""
userTest/ingest_knowledge.py
============================
Optimized Batch Ingestion for AuroraGraph.

Improvements:
- BATCH Embedding: ~10x faster than individual calls.
- Progress Logs: Shows exactly which chunk/page is being processed.
- Thread-Safe Kùzu: Handles concurrent writes via lock.
"""

import argparse
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

# Let the module find the local 'auragraph' src if not installed as a package.
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

try:
    from dotenv import load_dotenv

    from auragraph import AuroraGraphEngine
    from auragraph.core.config import config
    from auragraph.db.kuzu import KuzuDB
    from auragraph.ingestion.extractor import extract_triples
    from auragraph.ingestion.parsers import extract_chunks
    from auragraph.providers.embeddings.fastembed_provider import FastEmbedProvider
except ImportError as e:
    print(f"Error: {e}. Please ensure dependencies are installed (uv sync).")
    sys.exit(1)

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Thread-safety for DB writes
_db_lock = threading.Lock()


def ingest_file(file_path: Path, engine: AuroraGraphEngine, skip_triples: bool = False) -> dict:
    """
    Ingests a single file with batching and progress reporting.
    """
    fname = file_path.name
    size_mb = file_path.stat().st_size / (1024 * 1024)
    start = time.perf_counter()

    with _db_lock:
        already_done = engine.db.is_ingested(fname)

    if already_done:
        return {"filename": fname, "size_mb": size_mb, "duration": None, "status": "cached"}

    try:
        print(f"  📖 [{fname}] Parsing chunks...")
        chunks = extract_chunks(str(file_path))
        chunk_count = len(chunks)

        if chunk_count == 0:
            return {"filename": fname, "size_mb": size_mb, "duration": 0, "status": "empty"}

        # 1. Batch Embedding (Massive speedup)
        print(f"  🧠 [{fname}] Embedding {chunk_count} chunks (Batch mode)...")
        texts = [c["content"] for c in chunks]
        embeddings = []
        if engine.embedder:
            embeddings = engine.embedder.embed_batch(texts)
        else:
            embeddings = [None] * chunk_count

        # 2. Sequential Extraction & Insertion
        print(f"  🏗️  [{fname}] Extracting triples & Saving to Graph...")
        for i, chunk in enumerate(chunks):
            # Show progress every 50 chunks or on small files
            if i % 50 == 0 or chunk_count < 50:
                print(f"     └─ {fname}: {i}/{chunk_count} chunks processed")

            triples = []
            if not skip_triples:
                try:
                    triples = extract_triples(chunk["content"])
                except Exception:
                    pass

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


def build_report(results: list, workers: int, device: str, total_elapsed: float) -> str:
    run_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# AuroraGraph Ingestion Report\n",
        f"**Run at:** {run_at}  ",
        f"**Device:** `{device.upper()}`  ",
        f"**Workers (concurrency):** `{workers}`  ",
        f"**Total elapsed:** `{total_elapsed:.2f}s`\n",
        "| Filename | Size (MB) | Time | Status |",
        "| :--- | ---: | ---: | :--- |",
    ]
    for r in results:
        dur = f"{r['duration']:.2f}s" if r["duration"] is not None else "—"
        lines.append(f"| {r['filename']} | {r['size_mb']:.2f} | {dur} | {r['status']} |")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Parallel Ingestion for AuroraGraph")
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--device", type=str, default=None)
    parser.add_argument("--no-triples", action="store_true", help="Skip triple extraction for speed")
    args = parser.parse_args()

    workers = args.workers if args.workers is not None else config.AURA_CONCURRENCY
    if workers == 0:
        workers = os.cpu_count() or 4
    if args.device:
        os.environ["AURA_DEVICE"] = args.device

    knowledge_path = Path(__file__).resolve().parent / "knowledge"
    report_path = Path(__file__).resolve().parent / "report_time.md"
    db_path = Path(__file__).resolve().parent / "auragraph_graph"

    files = sorted(f for f in knowledge_path.iterdir() if f.suffix.lower() in [".pdf", ".txt", ".md"])
    if not files:
        print("Empty knowledge folder.")
        return

    print("🚀 Initializing AuroraGraph (Kùzu + FastEmbed)...")
    embedder = FastEmbedProvider()
    engine = AuroraGraphEngine(db=KuzuDB(str(db_path)), embedder=embedder)
    actual_device = getattr(embedder, "device", config.AURA_DEVICE)

    print(f"🔧 Concurrency: {workers} | Device: {actual_device.upper()} | Triples: {not args.no_triples}")
    print(f"📁 Source: {knowledge_path}\n")

    results = []
    overall_start = time.perf_counter()

    try:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_file = {executor.submit(ingest_file, f, engine, args.no_triples): f for f in files}
            for future in as_completed(future_to_file):
                res = future.result()
                results.append(res)
                dur = f"{res['duration']:.2f}s" if res["duration"] is not None else "cached"
                print(f"  🏁 FINISHED: {res['filename']} in {dur}")
    except KeyboardInterrupt:
        print("\n🛑 Ingestion interrupted by user. Saving partial report...")

    total_elapsed = time.perf_counter() - overall_start
    results.sort(key=lambda r: r["filename"])
    report = build_report(results, workers, actual_device, total_elapsed)
    report_path.write_text(report, encoding="utf-8")

    print(f"\n📊 Report: {report_path}")
    print(f"⏱️ Total wall time: {total_elapsed:.2f}s")


if __name__ == "__main__":
    main()
