"""Shared pytest fixtures for the AuroraGraph9D eval suite."""

import json
import os
import sys

import pytest

# Ensure `src/` is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from main import AuraGraphJIT  # noqa: E402

GOLDEN_DATASET_PATH = os.path.join(os.path.dirname(__file__), "golden_dataset.json")
TEST_DOCS_DIR = os.path.join(os.path.dirname(__file__), "test_docs")
EVAL_DB_PATH = os.path.join(os.path.dirname(__file__), "eval_test.db")


@pytest.fixture(scope="session")
def aura():
    """
    Session-scoped AuraGraphJIT instance.
    Creates a fresh eval database and ingests the test_docs/ folder
    so every test runs against our controlled, known content.
    """
    # Remove stale eval DB so we always start clean
    if os.path.exists(EVAL_DB_PATH):
        os.remove(EVAL_DB_PATH)

    engine = AuraGraphJIT(db_path=EVAL_DB_PATH, model_name="llama3.1:8b")

    # Ingest our controlled test documents
    if os.path.isdir(TEST_DOCS_DIR):
        engine.ingest_folder(TEST_DOCS_DIR)

    return engine


@pytest.fixture(scope="session")
def golden_dataset():
    """Load the golden evaluation dataset."""
    with open(GOLDEN_DATASET_PATH, encoding="utf-8") as f:
        return json.load(f)
