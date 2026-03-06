# AuroraGraph10D: Architecture & Codebase Audit (Proposed Improvements)

Following a comprehensive audit of `src/main.py` and the evaluation results, we have identified several architectural bottlenecks and opportunities to evolve this experimental proof-of-concept into a robust, production-ready reasoning engine.

## 1. Implement True "10D Synapse" Knowledge Graphs
**Current State:** 
The application claims "10D Synapses" and "Metabolic Filtering", but the underlying database (`auragraph_jit.db`) is currently a flat, 2D SQLite table running an FTS5 BM25 keyword search.
**Proposed Improvement:**
To achieve actual 10-dimensional graph traversal:
- Migrate to a native graph database structure (e.g., using `NetworkX` serialized to SQLite, or bridging to Neo4j/NebulaGraph).
- During ingestion, insert an Information Extraction (IE) pipeline (e.g., `llama-index` Property Graphs or `GLiNER`) that processes text into `(Subject) -> [Predicate] -> (Object)` triples.
- A true graph structure will allow multi-hop reasoning (e.g., linking a financial metric in a 2024 report mathematically to a 2025 report without keyword overlap).

## 2. Introduce Intelligent Chunking for Plain Text
**Current State:** 
PDFs are chunked page-by-page. However, Markdown (`.md`) and Text (`.txt`) files are ingested as a single massive string into one SQLite row (assigned to `page_num=1`).
**Proposed Improvement:**
- If you ingest a 10MB `.txt` file (like a server log or a book), FTS5 `snippet()` will have to parse a gigantic row in memory.
- We must implement an intelligent text splitter (e.g., by paragraph, Markdown header (`##`), or a fixed token limit like 1024 tokens) before inserting into the `anchors` table. This simulates "pages" for massive plain-text files and drastically speeds up SQLite retrieval.

## 3. Hybrid Search (Semantic Embeddings + FTS5 Keyword)
**Current State:** 
Retrieval relies 100% on FTS5 BM25 exact keyword matching, augmented by Porter Stemming. While phenomenally fast (~3ms) and anti-hallucinatory, it has poor **Recall** for semantic concepts. If the user asks about "financial decline" and the text says "revenue dropped," FTS5 returns 0 matches.
**Proposed Improvement:**
- Integrate a fast, local embedding model (e.g., `all-MiniLM-L6-v2` via `sentence-transformers`).
- Use SQLite's `vss` (Vector Search) extension or purely maintain an in-memory index like FAISS.
- Run queries through both Vector Search (high recall) and FTS5 (high precision), and use Cross-Encoder Reciprocal Rank Fusion (RRF) to blend the context blocks.

## 4. Query Expansion (Agent/MCP Driven)
**Current State:** 
The core engine strips hardcoded stop words (`what`, `were`, `done`, `time`, etc.) and performs basic keyword/vector matching. Baking an LLM into the retrieval path makes the library slow and tightly coupled.
**Proposed Improvement:**
- **Remove from Core**: Do not force LLM query rewriting inside the database retrieval logic. AuroraGraph should remain a high-speed, agnostic 10D retrieval mechanism.
- **MCP Server Logic**: Instead, implement Query Expansion as an instruction prompt or logic step within the future **AuroraGraph MCP Server**. The calling agent analyzing the user's intent should be responsible for parallelizing expanded search queries to the engine (e.g., calling `search("hardware margins")` and `search("revenue drop")` based on its own reasoning).

## 5. Streaming UI for Generation
**Current State:** 
Ollama is called with `stream=False`. Because the 8B LLM takes ~58 seconds to reason over 256k contexts, the user is left staring at a blank console.
**Proposed Improvement:**
- Toggle `stream=True` in the `ollama.generate()` call.
- Yield tokens directly to `sys.stdout` so the user sees the audit report being typed out in real-time. This reduces perceived latency from 60 seconds to ~1 second (Time to First Token).

## 6. Metabolic Filtering Implementation
**Current State:** 
Currently, all text `len(text) > 20` is indiscriminately inserted into the graph.
**Proposed Improvement:**
- Implement the "Metabolic Filtering" concept described in the README by running local NLP metrics (e.g., spaCy Named Entity Recognition density, TF-IDF scores) on chunks before insertion.
- Only allow "information-dense" chunks into the database (e.g., filtering out table-of-contents, boilerplate copyright text, or low-entropy fluff).

## 7. High-Performance Core Engine (Rust Integration)
**Current State:** 
String operations, stemming, and database queries are currently written purely in Python, which is fine for a PoC but may bottleneck as the graph scales to billions of nodes.
**Proposed Improvement:**
- Rewrite the core math, metabolic filtering, and 10D synaptic traversal algorithms in **Rust**, exposing them to Python via PyO3 (similar to how `ruff` or `pydantic-core` is built).
- This ensures the CPU-intensive graph mapping and filtering runs at near bare-metal C-level speeds, keeping the "JIT Engine" truly instantaneous while preserving Python's ease-of-use for the orchestration layers.

---

## The Production Roadmap: Step-by-Step Evolution

To move from this experimental PoC to the final production-ready `AuroraGraph10D` system, follow these sequential steps:

### Phase 1: Architectural Restructuring
Split the monolithic `main.py` into a proper, modular Python package:
```text
src/
├── core/             # Math Engine, Filtering Algorithms (prep for Rust)
├── db/               # Graph DB connectors (Neo4j / NebulaGraph)
├── ingestion/        # Extractors, Chunkers, Parsers
├── generation/       # LLM orchestration, Streamers
├── tools/            # Query rewriting, Prompts
└── main.py           # CLI entry point
```

### Phase 2: Database Migration Strategy
We must choose the graph DB based on scale:
- **Choose Neo4j:** If we prioritize extremely complex multi-hop queries right away and want rich visualization tools (Neo4j Bloom). Best for rapid development of the 10D logic.
- **Choose NebulaGraph:** If we anticipate distributed, massive-scale data (billions of nodes) from day one and prioritize raw ingestion/retrieval speed.
- **Action:** Migrate the SQLite writes to `Cypher` (Neo4j) or `nGQL` (NebulaGraph) statements.

### Phase 3: Ingestion Pipeline & Embeddings
1. Integrate `all-MiniLM-L6-v2` locally using `sentence-transformers`.
2. Integrate an Information Extraction framework (e.g., LlamaIndex or simple SpaCy triples extraction) to convert unstructured text into `(Subject)-[Predicate]->(Object)` graph nodes.
3. Apply embeddings to the resulting nodes so that they can be searched both exactly (via string matching) and semantically (via cosine similarity).

### Phase 4: Re-integrate and Optimize (Rust Engine)
1. Port the heavy computational logic (like mathematical scoring of node relevance and metabolic parsing of new documents) into a Rust crate.
2. Bind the Rust crate back to Python.
3. Re-run our automated LLM-as-a-Judge Eval Suite (from `tests/test_auragraph.py`) to verify that the new Graph + Vector + Rust architecture maintains the zero-hallucination **1.00 Faithfulness** score while significantly boosting **Context Relevance**.
