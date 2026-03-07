import os
import sys
import time

import pytest

# Ensure `src/` is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from auragraph.core.engine import AuroraGraphEngine
from auragraph.db.sqlite import SQLiteFTS5DB
from auragraph.providers.llm.ollama import OllamaProvider

LARGE_DOCS_DIR = os.path.join(os.path.dirname(__file__), "test_docs_large")
EVAL_LARGE_DB_PATH = os.path.join(os.path.dirname(__file__), "eval_large.db")


@pytest.fixture(scope="module")
def large_aura():
    """
    Module-scoped AuraGraphJIT instance for large-scale ingestion testing.
    This fixture ensures we start with a clean 9D index, ingests the massive
    Gutenberg text file, and measures the raw SQLite/FTS5 insertion speed.
    """
    if not os.path.exists(LARGE_DOCS_DIR) or not os.listdir(LARGE_DOCS_DIR):
        pytest.skip(f"No large files found in {LARGE_DOCS_DIR}. Run 'python download_large_file.py' first.")

    if os.path.exists(EVAL_LARGE_DB_PATH):
        try:
            os.remove(EVAL_LARGE_DB_PATH)
        except PermissionError:
            print(f"[!] Reusing existing DB {EVAL_LARGE_DB_PATH} because it is locked.")

    from auragraph.core.config import config

    # Instantiate the JIT Engine with DI
    if config.AURA_DB_PROVIDER == "neo4j":
        from auragraph.db.neo4j import Neo4jDB

        db_provider = Neo4jDB(config.NEO4J_URI, config.NEO4J_USER, config.NEO4J_PASSWORD)
    else:
        db_provider = SQLiteFTS5DB(db_path=EVAL_LARGE_DB_PATH)

    llm_provider = OllamaProvider(model_name=config.AURA_MODEL)
    engine = AuroraGraphEngine(db=db_provider, llm=llm_provider)

    # Time the exact ingestion speed for the massive directory
    start_t = time.time()
    engine.ingest_folder(LARGE_DOCS_DIR)
    ingest_ms = (time.time() - start_t) * 1000
    print(f"\n[BENCHMARK] Massive Gutenberg Text Ingest Time: {ingest_ms:.0f} ms")

    # Audit the SQLite DB size
    db_size_mb = os.path.getsize(EVAL_LARGE_DB_PATH) / (1024 * 1024)
    print(f"[BENCHMARK] eval_large.db Size on Disk: {db_size_mb:.2f} MB")

    return engine


@pytest.mark.evaluation
def test_large_file_retrieval_speed(large_aura):
    """
    Queries for a very specific phrase buried inside the massive 5.5MB
    Complete Works of William Shakespeare text to benchmark FTS5 snippet extraction.
    """
    query = "What is the specific quote about a horse by Richard III?"

    # We only care about the programmatic predict() speeds for retrieval
    # Note: the generative LLM step takes a long time, but we are benching
    # the SQLite FTS5 index 'retrieval_ms' here.
    prediction = large_aura.predict(query)

    assert len(prediction["context"]) > 0, "Failed to retrieve context from the massive file!"

    print(f"\n[BENCHMARK] Massive File Retrieval Speed: {prediction['retrieval_ms']:.2f} ms")
    print(f"[BENCHMARK] FTS5 found {len(prediction['context'])} highly relevant context blocks.")

    # Assert FTS5 Retrieval is still blazing fast even with a 5.5MB file (e.g. under 50ms)
    assert prediction["retrieval_ms"] < 50.0, f"Retrieval took too long: {prediction['retrieval_ms']}ms"

    # Print the specific extracted snippet to debug what context it grabbed
    print("\n--- FTS5 SNIPPET SAMPLE ---")
    print(prediction["context"][0])
    print("---------------------------")
