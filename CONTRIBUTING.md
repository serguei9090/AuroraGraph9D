# Contributing to AuroraGraph

Thank you for your interest in contributing! This guide will help you get set up.

## 🛠️ Prerequisites

| Tool | Install |
| :--- | :--- |
| **Rust** | [rustup.rs](https://rustup.rs) |
| **uv** | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Ollama** | [ollama.com](https://ollama.com) (for LLM tests) |

## 🚀 Local Setup

```bash
# 1. Clone the repo
git clone https://github.com/serguei9090/AuroraGraph9D
cd AuroraGraph9D

# 2. Install all deps including dev group
uv sync --group dev

# 3. Build the Rust extension in development mode
uv run maturin develop --release

# 4. Run the full test suite
uv run pytest tests/ -v

# 5. Lint
uv run ruff check .
```

## 📁 Project Structure

```
src/auragraph/
├── core/        # Engine orchestrator + config
├── db/          # Tri-Modal database backends (SQLite, Kùzu, Neo4j)
├── ingestion/   # Rust-backed chunking + metabolic filtering
├── providers/   # LLM & Embedding provider adapters
├── cli.py       # `auragraph` CLI entry point
└── app.py       # FastAPI server + Prometheus endpoint

src-rust/        # Rust extension source (PyO3)
tests/           # pytest suite
docs/            # Extended documentation
```

## 🧪 Testing

```bash
# Full suite
uv run pytest tests/ --cov=auragraph -v

# Rust parser tests only
uv run pytest tests/test_parsers.py -v

# Run benchmarks
uv run python tests/benchmark.py
```

## 📦 Building a Wheel Locally

```bash
# Produce a release wheel in ./dist/
uv run maturin build --release --out dist
```

## 📝 Conventions

- **Style**: Code is enforced by `ruff`. Run `uv run ruff check --fix .` before committing.
- **Commits**: Follow [Conventional Commits](https://www.conventionalcommits.org/) (e.g., `feat:`, `fix:`, `docs:`).
- **Tests**: New features must include at least one test in `tests/`.
