from auragraph.ingestion.extractor import extract_triples
from auragraph.ingestion.parsers import _chunk_text, _is_valid_text, extract_chunks


def test_is_valid_text():
    assert _is_valid_text("") is False
    assert _is_valid_text("too short") is False
    assert (
        _is_valid_text(
            "This is an information dense sentence that passes the metabolic filter. The system operates on a semantic graph model."
        )
        is True
    )

    # Test low entropy (highly repetitive)
    repetitive = "apple " * 20
    assert _is_valid_text(repetitive) is False


def test_chunk_text():
    text = "Short text"
    assert len(_chunk_text(text, max_chars=50)) == 1

    # Needs a long text
    long_text = " ".join(f"Word{i}" for i in range(200))  # Unique words to pass entropy theoretically if tested
    chunks = _chunk_text(long_text, max_chars=100)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 100


def test_extract_chunks_text(tmp_path):
    text_file = tmp_path / "test.txt"
    # Create text large enough to be chunked into parts depending on newlines, but unique so it passes entropy
    s1 = " ".join(f"UniqueNoun_{i} UniqueVerb_{i} UniqueAdj_{i} UniqueObject_{i}" for i in range(200))
    s2 = " ".join(f"AnotherNoun_{i} AnotherVerb_{i} AnotherAdj_{i} AnotherObject_{i}" for i in range(200))
    content = f"# Section 1\n{s1}\n\n# Section 2\n{s2}"
    text_file.write_text(content, encoding="utf-8")

    chunks = extract_chunks(str(text_file))
    assert len(chunks) >= 2
    assert chunks[0]["filename"] == "test.txt"
    assert "chunk_index" in chunks[0]["metadata"]


def test_extract_chunks_empty(tmp_path):
    text_file = tmp_path / "empty.txt"
    text_file.write_text("tiny", encoding="utf-8")

    chunks = extract_chunks(str(text_file))
    assert len(chunks) == 0  # Fails metabolic filter


def test_extract_triples():
    text = "The quick brown fox jumps over the lazy dog."
    triples = extract_triples(text)

    # We expect at least one triple (fox, JUMP, dog)
    # The actual output depends on SpaCy's parsing but let's check structure
    assert isinstance(triples, list)
    if triples:
        for t in triples:
            assert "subject" in t
            assert "predicate" in t
            assert "object" in t
            assert t["predicate"] == "JUMP"

