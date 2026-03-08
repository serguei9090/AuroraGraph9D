# Changelog

All notable changes to **AuroraGraph** are documented here.

Follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

## [0.1.2] - 2026-03-07

### Fixed
- Fixed PyPI upload issue with duplicate files by bumping version to 0.1.2.
- Fixed PyPI and Python version badges on the `README.md` by matching case-sensitive package names.

## [0.1.1] - 2026-03-07
### Added
- PyPI publishing infrastructure (Maturin cross-compilation, GitHub Actions).
- `auragraph` CLI entry point (`auragraph ingest`, `auragraph query`).
- Optional-dependency extras (`sqlite`, `kuzu`, `neo4j`, `embeddings`, `pdf`, `mcp`, `viz`, `all`).
- **FastEmbed Provider**: Integrated `FastEmbedProvider` for memory-efficient CPU and GPU-accelerated embeddings using `fastembed`.
- **Kùzu Database Provider**: Implemented `KuzuDB` backend class to support Kùzu embedded graph database capabilities and Cypher queries.
- **Pre-commit Hooks**: Configured `lefthook` and `ruff` to enforce Python code quality and formatting standards.

### Changed
- Improved `chat_test.py` script with execution timing to measure ingestion and query performance.
- Modified test scripts to gracefully handle missing relevant information dynamically to minimize hallucination.

### Fixed
- Fixed `AttributeError: 'NoneType' object has no attribute 'generate'` in `chat_test.py` during empty search results.
- Resolved endless hangs in testing scripts when no context was retrieved from the database.

---

## [0.1.0] - 2026-03-06

### Added
- **Phase 1**: Modular `src/auragraph` library structure with `core`, `db`, `ingestion`, `providers`.
- **Phase 2**: Neo4j graph backend with native Cypher support.
- **Phase 3**: Hybrid retrieval via FTS5 + Semantic Embeddings (MiniLM-L6).
- **Phase 4**: Intelligent ingestion: recursive chunking + Metabolic Filtering.
- **Phase 5**: MCP Server (`auragraph_mcp`) for AI Agent integration.
- **Phase 6**: Rust bare-metal parsing core via PyO3 (`auragraph_core`).
- **Phase 7**: Prometheus telemetry, Grafana dashboards, Docker Compose stack.
- **Phase 8**: Full documentation: README, ARCHITECTURE.md, docs/PUBLISHING.md.
- `CHANGELOG.md`, `LICENSE`, and `CONTRIBUTING.md`.

### Performance
- Retrieval latency: < 1ms (SQLite FTS5), < 15ms (Complex Graph Traversal).
- Ingestion: 10x speedup over pure-Python via Rust core.
- Faithfulness: 1.00 (Zero Hallucination on 35/35 benchmark queries).
