from unittest.mock import ANY, MagicMock

import pytest

from auragraph.core.engine import AuroraGraphEngine
from auragraph.db.base import BaseGraphDB
from auragraph.db.sqlite import SQLiteFTS5DB
from auragraph.providers.embeddings.base import BaseEmbeddingProvider
from auragraph.providers.llm.base import BaseLLMProvider


@pytest.fixture
def mock_db():
    db = MagicMock(spec=BaseGraphDB)
    return db

@pytest.fixture
def mock_llm():
    llm = MagicMock(spec=BaseLLMProvider)
    return llm

@pytest.fixture
def mock_embedder():
    embedder = MagicMock(spec=BaseEmbeddingProvider)
    return embedder

def test_engine_initialization(mock_db, mock_llm, mock_embedder):
    engine = AuroraGraphEngine(db=mock_db, llm=mock_llm, embedder=mock_embedder)
    assert engine.db == mock_db
    assert engine.llm == mock_llm
    assert engine.embedder == mock_embedder

def test_engine_predict_logic(mock_db, mock_llm, mock_embedder):
    # Setup mock returns
    mock_db.search.return_value = [{"filename": "test.txt", "page": 1, "text": "Extracted context"}]
    mock_llm.generate.return_value = "Generated response"

    engine = AuroraGraphEngine(db=mock_db, llm=mock_llm, embedder=mock_embedder)
    # Use words that are NOT in stop_words to avoid early return
    result = engine.predict("Find quantum physics")

    assert result["response"] == "Generated response"
    assert len(result["context"]) == 1
    # Engine wraps text in SOURCE/TEXT template
    assert "Extracted context" in result["context"][0]
    assert "retrieval_ms" in result
    assert "generation_ms" in result



def test_sqlite_db_basic(tmp_path):
    db_file = tmp_path / "test.db"
    db = SQLiteFTS5DB(str(db_file))

    # Test insertion
    db.insert_document("doc1.txt", "This is some content to search for.", {"page": 1})

    assert db.is_ingested("doc1.txt") is True
    assert db.is_ingested("absent.txt") is False

    # Test search
    results = db.search(["content"], limit=5, snippet_words=10)
    assert len(results) > 0
    assert "content" in results[0]["text"]
    assert results[0]["filename"] == "doc1.txt"

def test_engine_ingest_logic(mock_db, mock_embedder, tmp_path):
    # Setup files
    doc = tmp_path / "doc.txt"
    doc.write_text("This is a valid piece of text that should pass the metabolic filter and be ingested.", encoding="utf-8")

    mock_db.is_ingested.return_value = False

    engine = AuroraGraphEngine(db=mock_db, embedder=mock_embedder)
    engine.ingest_folder(str(tmp_path))

    assert mock_db.insert_document.called

def test_engine_custom_prompt(mock_db, mock_llm, mock_embedder):
    mock_db.search.return_value = [{"filename": "test.txt", "page": 1, "text": "evidence text"}]
    mock_llm.generate.return_value = "custom response"

    engine = AuroraGraphEngine(db=mock_db, llm=mock_llm, embedder=mock_embedder)
    custom_p = "Query: {query}, Evidence: {evidence}"

    # Use non-stop words
    result = engine.predict("quantum mechanics", custom_prompt=custom_p)

    assert result["response"] == "custom response"
    # Verify generate was called with formatted prompt
    expected_prompt = "Query: quantum mechanics, Evidence: SOURCE: test.txt (Page 1)\nTEXT: evidence text\n"
    mock_llm.generate.assert_called_with(expected_prompt, ANY, stream=False)


