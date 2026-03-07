# AuroraGraph — Code Examples 🚀

This directory contains standalone scripts demonstrating how to use the AuroraGraph library for various tasks.

## 📂 Examples

| File | Description |
|:---|:---|
| [`ingest_knowledge.py`](./ingest_knowledge.py) | **Production-Ready Ingestion**. Reference script for batch processing folders of PDFs, handling thread-safety, progress reporting, and database indexing. |
| [`simple_query.py`](./simple_query.py) | **Basic Search & Predict**. Minimal example of loading a database and asking a question. |
| [`minimal_ingest.py`](./minimal_ingest.py) | **Simple Ingestion**. A stripped-down version of the ingestion pipeline for learning purposes. |
| [`chat_test.py`](./chat_test.py) | **Interactive Chat**. A simple CLI loop for chatting with your knowledge base. |

## 🛠️ How to run

All examples are designed to be run via `uv run` from the project root.

```bash
# Ingest local knowledge (Kùzu DB + FastEmbed)
uv run python code_examples/ingest_knowledge.py --device cpu

# Query the database
uv run python code_examples/simple_query.py "What is AWS VPC?"
```

## 🗃️ Data & Databases

- **`knowledge/`**: Put your source documents (PDF, TXT, MD) here for ingestion.
- **`auragraph_graph/`**: This is the default folder where Kùzu stores the knowledge graph (created during ingestion).

---

## 💡 Configuration Tips

Most scripts read from your `.env` file. You can override settings via CLI flags (run with `--help`).

**Common flags:**
- `--device`: `cpu`, `cuda`, or `mps`.
- `--workers`: Number of parallel workers for ingestion.
- `--no-triples`: Disables the metabolic logic (faster ingestion, less granular graph).
