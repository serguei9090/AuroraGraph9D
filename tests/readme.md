# AuroraGraph9D Test Suite

This directory contains the testing and evaluation infrastructure for AuroraGraph9D. The suite is designed to balance fast developer feedback with deep semantic verification.

## 🧪 Test Categories

| Category | Files | Target | Frequency |
| :--- | :--- | :--- | :--- |
| **Unit Tests** | `test_parsers.py`, `test_engine_unit.py`, `test_api.py` | Core logic, chunking, API, mocking | Every commit |
| **Evaluation** | `test_auragraph.py` | RAG accuracy (LLM-as-a-Judge) | Before release |
| **Benchmarks** | `test_large_scale.py` | Performance at scale | Performance tuning |
| **Utilities** | `test_ollama.py`, `benchmark.py` | Connectivity & raw speed | Debugging |

## 🚫 Excluded Tests

By default, **Evaluation** and **Benchmark** tests are excluded from the standard test run. These are marked with `@pytest.mark.evaluation` in the code and filtered in `pyproject.toml`.

### Why they are excluded:
1. **Resource Heavy:** They require a local LLM (Ollama) or external API to be running.
2. **Slow:** The golden dataset evaluation can take several minutes to grade.
3. **Non-Deterministic:** Evaluation scores may vary slightly between runs due to LLM variance.

---

## 🚀 How to Run

### 1. Fast Unit Tests (Recommended for dev)
Runs only the deterministic logic tests that don't require an LLM.
```bash
uv run pytest
```

### 2. Full Evaluation Suite
Runs the LLM-as-a-Judge scorecard against the golden dataset.
```bash
uv run pytest -m evaluation -s
```

### 3. Coverage Analysis
Check which lines of code are actually being executed by your tests.
```bash
uv run pytest --cov=src --cov-report=term-missing
```

### 4. Large Scale Benchmark
Benchmarks ingestion of massive text files (requires downloading the dataset first).
```bash
python download_large_file.py
uv run pytest tests/test_large_scale.py -m evaluation -s
```

---

## 🏗️ Mocking Strategy

For unit tests that don't require an LLM, we use `unittest.mock`. This is crucial for CI/CD environments where Ollama might not be available.

**Example: Mocking the Engine**
When testing the API, we patch the engine class *before* importing the app to prevent the real engine from attempting to initialize (which might cause IO lock errors on the DB):
```python
with patch("auragraph.core.engine.AuroraGraphEngine") as MockEngine:
    mock_instance = MockEngine.return_value
    from auragraph.app import app
```

