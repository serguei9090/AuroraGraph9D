# AuroraGraph — Library Usage Guide 📚

> **This guide is for end users who installed `auragraph` from PyPI.**  
> For contributor / development setup, see [README.md](./README.md).

---

## Installation

```bash
# Minimal — SQLite, CPU embeddings
pip install "auragraph[fastembed]"

# Recommended production setup — Kùzu graph + CPU FastEmbed
pip install "auragraph[kuzu,fastembed]"

# NVIDIA GPU — see GPU section below
pip install "auragraph[cuda]"

# Neo4j enterprise cluster
pip install "auragraph[neo4j,fastembed]"

# Everything
pip install "auragraph[all]"
```

With **uv**:
```bash
uv add "auragraph[kuzu,fastembed]"
```

---

## GPU Setup (NVIDIA CUDA 12)

After installing the `[cuda]` extra, you need two additional steps because
the standard PyPI `onnxruntime-gpu` targets CUDA 11, and cuDNN is not bundled.

### Windows & Linux

```bash
# Step 1 — CUDA 12 onnxruntime-gpu (Python 3.13 compatible nightly)
pip install onnxruntime-gpu \
  --index-url https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/onnxruntime-cuda-12/pypi/simple/ \
  --pre

# Step 2 — cuDNN 9 as a Python wheel (no separate system install required)
pip install "nvidia-cudnn-cu12>=9.1.0"
```

On **Linux**, you can instead install cuDNN via your package manager and skip step 2:
```bash
# Ubuntu/Debian
sudo apt install cudnn9-cuda-12
```

---

## Advanced Documentation 

If you want to configure Database routing (Kùzu, SQLite, Neo4j), inject custom Embedders, change RAG variables, or create custom dynamic prompts, see our detailed documentation:

1. [Configuration & Dependency Injection](docs/configuration.md)
2. [Customizing System & Generation Prompts](docs/custom_prompts.md)
3. [Library Publishing Guide (GitHub Actions)](docs/publish_library.md)
4. [LangChain vs AuroraGraph Performance Benchmarks](comparison/comparison_result_test.md)

---

## Configuration

AuroraGraph is configured via **environment variables** or a `.env` file in
your project root. Create a `.env` file:

```ini
# ── LLM ───────────────────────────────────────────────────────────
AURA_MODEL=llama3.1:8b          # any Ollama model name

# ── Database backend ───────────────────────────────────────────────
AURA_DB_PROVIDER=kuzu            # sqlite | kuzu | neo4j

# Kùzu path (when AURA_DB_PROVIDER=kuzu)
KUZU_DB_PATH=./my_graph

# Neo4j connection (when AURA_DB_PROVIDER=neo4j)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=yourpassword

# ── Embeddings ─────────────────────────────────────────────────────
AURA_DEVICE=auto                 # auto | cpu | cuda | mps

# ── Search tuning ──────────────────────────────────────────────────
FTS5_MATCH_LIMIT=25              # max chunks returned per query
FTS5_SNIPPET_WORDS=200           # words per snippet
AURA_CONCURRENCY=4               # parallel ingest workers (0=all cores)
```

---

## Quick Start

### Ingest documents and query

```python
from dotenv import load_dotenv
load_dotenv()  # load .env from project root

from auragraph import AuroraGraphEngine
from auragraph.db.kuzu import KuzuDB
from auragraph.providers.embeddings.fastembed_provider import FastEmbedProvider

# Build the engine with your chosen backend and embedder
engine = AuroraGraphEngine(
    db=KuzuDB("./my_knowledge_graph"),
    embedder=FastEmbedProvider(),          # uses AURA_DEVICE from env
)

# Ingest a folder of PDFs, TXTs or MD files
engine.ingest_folder("./my_docs")

# Interactive query (streams to console)
engine.query("What are the main AWS cost optimisation strategies?")
```

### Programmatic query (get structured result)

```python
result = engine.predict("Explain VPC peering vs Transit Gateway")

print(result["response"])        # LLM answer
print(result["sources"])         # list of {filename, page}
print(result["retrieval_ms"])    # retrieval latency
print(result["generation_ms"])   # LLM generation latency
```

---

## Choosing a Database Backend

### SQLite (built-in, zero setup)

Best for local testing. No extra install required.

```python
from auragraph import AuroraGraphEngine
from auragraph.db.sqlite import SQLiteFTS5DB

engine = AuroraGraphEngine(
    db=SQLiteFTS5DB("./knowledge.db"),
)
```

Install:
```bash
pip install "auragraph[fastembed]"   # SQLite is always included
```

### Kùzu (recommended for production)

Embedded property graph. Full Hybrid Search (BM25 + HNSW vector). No Docker needed.

```python
from auragraph.db.kuzu import KuzuDB

engine = AuroraGraphEngine(
    db=KuzuDB("./my_graph"),   # folder, created automatically
)
```

Install:
```bash
pip install "auragraph[kuzu,fastembed]"
```

### Neo4j (enterprise cluster)

For multi-node / cloud deployments. Requires a running Neo4j 5+ instance.

```python
import os
from auragraph.db.neo4j import Neo4jDB

engine = AuroraGraphEngine(
    db=Neo4jDB(
        uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        user=os.getenv("NEO4J_USER", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "password"),
    ),
)
```

Install:
```bash
pip install "auragraph[neo4j,fastembed]"
```

---

## Choosing an Embedding Backend

### FastEmbed — CPU (recommended, ~100 MB)

Rust + ONNX Runtime, no PyTorch. Fast and lightweight.

```python
from auragraph.providers.embeddings.fastembed_provider import FastEmbedProvider

embedder = FastEmbedProvider()             # device from AURA_DEVICE env var
embedder = FastEmbedProvider(device="cpu") # force CPU
```

Install: `pip install "auragraph[fastembed]"`

### FastEmbed — NVIDIA GPU (CUDA 12)

```python
embedder = FastEmbedProvider(device="cuda")
```

Install: see [GPU Setup](#gpu-setup-nvidia-cuda-12) above.

### FastEmbed — Apple Silicon (MPS)

```python
embedder = FastEmbedProvider(device="mps")
```

Install: `pip install "auragraph[mps]"`

### sentence-transformers / PyTorch (~2 GB)

```python
from auragraph.providers.embeddings.local import LocalEmbeddingProvider

embedder = LocalEmbeddingProvider(device="cuda")  # or "cpu", "mps"
```

Install: `pip install "auragraph[embeddings]"`

### No embeddings (keyword-only search)

Pass `embedder=None`. Only BM25 FTS will run (no vector search).

```python
engine = AuroraGraphEngine(db=KuzuDB("./graph"), embedder=None)
```

---

## Choosing an LLM Provider

### Ollama (default, local)

Runs a local LLM via [Ollama](https://ollama.ai). Start Ollama first:
```bash
ollama pull llama3.1:8b
```

```python
from auragraph.providers.llm.ollama import OllamaProvider

engine = AuroraGraphEngine(
    db=KuzuDB("./graph"),
    llm=OllamaProvider("llama3.1:8b"),
)
```

### Custom LLM provider

Implement `BaseLLMProvider` and inject it:

```python
from auragraph.providers.llm.base import BaseLLMProvider

class MyOpenAIProvider(BaseLLMProvider):
    def generate(self, prompt: str, system: str, stream: bool = False):
        # call your API here
        ...

engine = AuroraGraphEngine(
    db=KuzuDB("./graph"),
    llm=MyOpenAIProvider(),
)
```

---

## Batch Ingestion (high performance)

For large document sets, use the batch ingestion pattern with parallel workers
and `embed_batch()` instead of per-chunk embedding:

```python
from concurrent.futures import ThreadPoolExecutor
from auragraph.ingestion.parsers import extract_chunks

files = list(Path("./my_docs").glob("**/*.pdf"))
embedder = FastEmbedProvider(device="cuda")

def ingest_file(path):
    chunks = extract_chunks(str(path))
    texts = [c["content"] for c in chunks]
    embeddings = embedder.embed_batch(texts)   # single GPU call for all chunks
    for chunk, emb in zip(chunks, embeddings):
        engine.db.insert_document(
            filename=chunk["filename"],
            content=chunk["content"],
            metadata=chunk["metadata"],
            embedding=emb,
        )

with ThreadPoolExecutor(max_workers=4) as pool:
    list(pool.map(ingest_file, files))
```

See [`userTest/ingest_knowledge.py`](./userTest/ingest_knowledge.py) for a complete,
production-ready reference with progress reporting and idempotent re-ingestion.

---

## MCP Server (AI Agent Integration)

AuroraGraph can run as a **Model Context Protocol** server, exposing the
knowledge graph as a tool to any MCP-compatible AI agent (Claude, Cursor, etc.).

```bash
pip install "auragraph[mcp]"
```

```python
# Start the MCP server
from auragraph.mcp_server import create_mcp_server

server = create_mcp_server()
server.run()
```

---

## API Reference

### `AuroraGraphEngine`

```python
AuroraGraphEngine(
    db: BaseGraphDB | None = None,           # defaults to AURA_DB_PROVIDER env
    llm: BaseLLMProvider | None = None,      # defaults to OllamaProvider
    embedder: BaseEmbeddingProvider | None = None,  # defaults to LocalEmbeddingProvider
)
```

| Method | Description |
|:---|:---|
| `ingest_folder(path)` | Scan and ingest all PDFs/TXTs/MDs in a folder |
| `query(text, stream=True)` | Console-friendly query with streaming output |
| `predict(text, stream=False)` | Programmatic query returning a structured dict |

### `predict()` return value

```python
{
    "query": str,           # original query
    "context": list[str],   # retrieved evidence blocks
    "response": str,        # LLM answer
    "sources": list[dict],  # [{filename, page}, ...]
    "retrieval_ms": float,  # hybrid search latency
    "generation_ms": float, # LLM generation latency
}
```

---

## Common Issues

### `No module named 'auragraph_core'`
The Rust extension was not compiled. Run:
```bash
uv tool run maturin develop
# or from a pip install, reinstall the package:
pip install --force-reinstall auragraph
```

### `ModuleNotFoundError: No module named 'kuzu'`
Install the `[kuzu]` extra:
```bash
pip install "auragraph[kuzu,fastembed]"
```

### `CUDAExecutionProvider failed — cudnn64_9.dll not found`
cuDNN 9 is missing. Install the Python wheel:
```bash
pip install "nvidia-cudnn-cu12>=9.1.0"
```

### Kùzu `Could not set lock on file`
Another process has the database open. Close all other scripts or open
only one `KuzuDB` instance per database folder at a time.

---

## License

MIT — [github.com/serguei9090/AuroraGraph9D](https://github.com/serguei9090/AuroraGraph9D)
