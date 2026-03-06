"""Shared pytest fixtures for the AuroraGraph9D eval suite."""

import json
import os
import sys

import pytest

# Ensure `src/` is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from auragraph.core.engine import AuroraGraphEngine  # noqa: E402
from auragraph.db.sqlite import SQLiteFTS5DB
from auragraph.providers.llm.ollama import OllamaProvider

GOLDEN_DATASET_PATH = os.path.join(os.path.dirname(__file__), "golden_dataset.json")
TEST_DOCS_DIR = os.path.join(os.path.dirname(__file__), "test_docs")
EVAL_DB_PATH = os.path.join(os.path.dirname(__file__), "eval_test.db")


@pytest.fixture(scope="session")
def aura():
    """
    Session-scoped AuraGraphJIT instance.
    Creates a fresh eval database and ingests the test_docs/ folder
    so every test runs against our controlled, known content.

    On Windows, if a previous process left the DB locked, we gracefully
    skip the cleanup and reuse it (ingestion is idempotent via file_tracking).
    """
    # Try to remove stale eval DB so we always start clean
    if os.path.exists(EVAL_DB_PATH):
        try:
            os.remove(EVAL_DB_PATH)
        except PermissionError:
            print(
                f"\n[!] Could not delete {EVAL_DB_PATH} (file locked by another process). "
                "Reusing existing DB — this is safe because ingestion is idempotent."
            )

    from auragraph.core.config import config

    # Instantiate our new DI providers
    if config.AURA_DB_PROVIDER == "neo4j":
        from auragraph.db.neo4j import Neo4jDB

        db_provider = Neo4jDB(config.NEO4J_URI, config.NEO4J_USER, config.NEO4J_PASSWORD)
    else:
        db_provider = SQLiteFTS5DB(db_path=EVAL_DB_PATH)

    llm_provider = OllamaProvider(model_name=config.AURA_MODEL)
    engine = AuroraGraphEngine(db=db_provider, llm=llm_provider)

    # Ingest our controlled test documents
    if os.path.isdir(TEST_DOCS_DIR):
        engine.ingest_folder(TEST_DOCS_DIR)

    return engine


@pytest.fixture(scope="session")
def golden_dataset():
    """Load the golden evaluation dataset."""
    with open(GOLDEN_DATASET_PATH, encoding="utf-8") as f:
        return json.load(f)
