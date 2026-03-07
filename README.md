# AuroraGraph 🌌

> **Disclaimer:** This is a personal learning project created for educational purposes and to explore different code concepts with AI concepts.
> - **Status:** Personal sandbox / Portfolio piece.
> - **License:** This project is open-source and available for public educational use under the MIT License.
> - **Purpose:** Academic research and technical skill development.

**High-Performance Knowledge Graph & Deterministic Reasoning Engine with a Rust Core.**

AuroraGraph combines a **Rust-Powered Parser**, **Multi-Dimensional Synaptic Links**, and **Hybrid Search** (BM25 + HNSW vector) to build a hallucination-free RAG pipeline on top of pluggable graph databases — SQLite, Kùzu, or Neo4j.

---

## 🗺️ Roadmap

**What's Next:**
- **Interactive Web UI:** Build a webpage with an interactive 3D view of the knowledge graph, featuring animations when information is retrieved during a query.
- **Neo4j Validation:** Conduct comprehensive user testing for the Neo4j database integration (currently implemented but pending user validation).

---

## 🏗️ Architecture

```
Raw Documents → Rust Parser + Metabolic Filter → Graph DB (Kùzu / SQLite / Neo4j)
                                                          ↓
User Query → AuroraGraph Engine → Hybrid Search (BM25 + Vector HNSW) → Ollama LLM → Answer
```

---

## 📦 Quick Install (from PyPI)

```bash
# CPU (recommended starting point)
pip install auragraph[fastembed]

# With Kùzu embedded graph (no Docker, recommended for production)
pip install "auragraph[kuzu,fastembed]"

# With Neo4j cluster
pip install "auragraph[neo4j,fastembed]"

# NVIDIA GPU — see GPU Setup below
pip install "auragraph[cuda]"
```

> For full library usage docs, see [README_LIBRARY.md](./README_LIBRARY.md).

---

## 🛠️ Development Setup (from source)

Requires: **uv** · **Rust toolchain** (`rustup.rs`)

```bash
git clone https://github.com/serguei9090/AuroraGraph9D.git
cd AuroraGraph9D
cp .env.example .env   # edit as needed
```

---

## 🗄️ Database Backend

Set `AURA_DB_PROVIDER` in `.env`:

| Value | Extra | Description |
|:---|:---|:---|
| `sqlite` | *(built-in)* | Dev / testing, no extras |
| `kuzu` | `--extra kuzu` | Embedded graph, zero Docker, recommended |
| `neo4j` | `--extra neo4j` | Enterprise cluster |

---

## 🖥️ Setup — Windows (CUDA 12 · Python 3.13)

### 1 · Prerequisites

| Requirement | Version | Download |
|:---|:---|:---|
| NVIDIA Driver | ≥ 580 | [nvidia.com/drivers](https://www.nvidia.com/drivers) |
| CUDA Toolkit | 12.x | [developer.nvidia.com/cuda-downloads](https://developer.nvidia.com/cuda-downloads) |
| Rust toolchain | stable | `winget install Rustlang.Rustup` |
| uv | latest | `winget install astral-sh.uv` |

Verify CUDA is on PATH:
```powershell
nvcc --version   # should show 12.x
nvidia-smi       # should show your GPU
```

### 2 · Install dependencies

```powershell
# Core deps + Kùzu graph + fastembed-gpu package
uv sync --extra cuda --extra kuzu

# Replace standard onnxruntime-gpu with the CUDA 12 nightly build
# (required because the stable PyPI wheel targets CUDA 11;
#  the nightly feed is the only source with Python 3.13 + CUDA 12 wheels)
uv pip install onnxruntime-gpu `
  --index-url https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/onnxruntime-cuda-12/pypi/simple/ `
  --index-strategy unsafe-best-match `
  --prerelease=allow

# Install cuDNN 9 as a Python wheel
# (CUDA Toolkit does NOT include cuDNN on Windows; this wheel puts the DLLs
#  where onnxruntime.preload_dlls() can find them automatically)
uv pip install "nvidia-cudnn-cu12>=9.1.0"
```

### 3 · Configure `.env`

```ini
AURA_DB_PROVIDER=kuzu
AURA_DEVICE=cuda
AURA_MODEL=llama3.1:8b
```

### 4 · Run ingestion

### 4 · Run ingestion

```powershell
uv run python code_examples/ingest_knowledge.py --device cuda
uv run python code_examples/chat_test.py
```

Expected output:
```
Initializing AuroraGraph (Kuzu + FastEmbed)...
[FastEmbed] ✅ CUDA available via fastembed-gpu (ONNX Runtime).
[FastEmbed] Loading model: BAAI/bge-small-en-v1.5
[FastEmbed] Device: CUDA (requested: 'cuda')
```

> **Note:** You may see harmless warnings about `cufft64_11.dll` or `cudart64_12.dll`
> not found during the DLL search sweep — these do not affect functionality.

---

## 🐧 Setup — Linux (CUDA 12 · Python 3.13)

### 1 · Prerequisites

Install NVIDIA drivers + CUDA 12 Toolkit using your distro's package manager, or the official runfile.

**Ubuntu / Debian:**
```bash
# CUDA Toolkit
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt update && sudo apt install cuda-toolkit-12-6

# cuDNN 9
sudo apt install cudnn9-cuda-12
```

**Verify:**
```bash
nvcc --version   # 12.x
nvidia-smi
```

Install **uv** and **Rust**:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

### 2 · Install dependencies

```bash
# Core deps + Kùzu + fastembed-gpu
uv sync --extra cuda --extra kuzu

# Replace with CUDA 12 onnxruntime-gpu nightly (Python 3.13 compatible)
uv pip install onnxruntime-gpu \
  --index-url https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/onnxruntime-cuda-12/pypi/simple/ \
  --index-strategy unsafe-best-match \
  --prerelease=allow

# cuDNN 9 wheel (alternative to system install if preferred)
# Skip this if you installed cudnn9-cuda-12 via apt above
uv pip install "nvidia-cudnn-cu12>=9.1.0"
```

### 3 · Configure `.env`

```ini
AURA_DB_PROVIDER=kuzu
AURA_DEVICE=cuda
AURA_MODEL=llama3.1:8b
```

### 4 · Run ingestion

```bash
uv run python code_examples/ingest_knowledge.py --device cuda
uv run python code_examples/chat_test.py
```

---

## 🍎 Setup — macOS (Apple Silicon MPS)

```bash
# Install uv + Rust
brew install uv
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Sync with MPS-optimised fastembed
uv sync --extra mps --extra kuzu
```

`.env`:
```ini
AURA_DB_PROVIDER=kuzu
AURA_DEVICE=mps
```

Run:
```bash
uv run python code_examples/ingest_knowledge.py --device mps
uv run python code_examples/chat_test.py
```

---

## 💡 CPU-Only Setup (any OS)

No GPU needed — FastEmbed on CPU is still fast (~100 MB install).

```bash
uv sync --extra fastembed --extra kuzu
uv run python code_examples/ingest_knowledge.py --device cpu
uv run python code_examples/chat_test.py
```

---

## 🌍 Environment Reference

Copy `.env.example` → `.env` and set:

| Variable | Default | Description |
|:---|:---|:---|
| `AURA_MODEL` | `llama3.1:8b` | Ollama model name |
| `AURA_DB_PROVIDER` | `sqlite` | `sqlite` / `kuzu` / `neo4j` |
| `AURA_DEVICE` | `auto` | `auto` / `cpu` / `cuda` / `mps` |
| `AURA_CONCURRENCY` | `4` | Parallel ingestion workers (0 = all cores) |
| `KUZU_DB_PATH` | `./auragraph_graph` | Kùzu database folder |
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j URI |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | `password` | Neo4j password |
| `FTS5_MATCH_LIMIT` | `25` | Max chunks returned per search |
| `FTS5_SNIPPET_WORDS` | `200` | Snippet size in words |

---

## 🚀 Docker (Full Stack)

```bash
cp .env.example .env
docker compose up --build -d
# API:        http://localhost:8000
# Prometheus: http://localhost:9090
# Grafana:    http://localhost:3000
```

---

## 📊 Benchmarks vs Traditional RAG (LangChain + FAISS)

AuroraGraph trades raw indexing speed for deterministic accuracy and zero hallucinations. While traditional setups simply chunk and dump files into an index, AuroraGraph parses Multi-Dimensional Synapses and enforces a strict Audit formatting pipeline. 

| Metric | LangChain + FAISS | AuroraGraph (Audit Mode) | AuroraGraph (Fast Mode) |
|---|---|---|---|
| **Answer Quality** | High Hallucination Risk (No citations) | **Zero Hallucinations** (Page-level citations) | High Accuracy |
| **Generation Speed** | ~18s | ~94s | **~19s** |
| **Indexing Speed** | ~69s | ~203s | *(Runs Once)* |
| **Retrieval Latency**| ~0.05s | ~0.12s | ~0.12s |

### Pros & Cons
**Why AuroraGraph is better:**
- **Zero Hallucination Guarantee:** By forcing the LLM into a two-task Audit Mode, it must prove where it found every fact.
- **Enterprise Traceability:** AuroraGraph provides the exact filename and page number so humans can verify the source in seconds.
- **Dynamic Speed:** You can toggle from the heavy Audit Mode to a hyper-fast traditional RAG prompt instantly by using `engine.query(custom_prompt="...")`. See [Custom Prompts Docs](docs/custom_prompts.md).

**Cons:**
- Upfront calculation of 10D Synaptic Edges and Nodes takes roughly 3x longer during the initial ingestion phase compared to simple text chunking arrays.
- Default `Generation` takes longer due to outputting structured, deterministic logs instead of simple paragraphs. 

*Read the full [Performance Benchmark Report](./comparison/comparison_result_test.md)*.

---

## ⚖️ License

MIT — High Performance, Zero Hallucination.
