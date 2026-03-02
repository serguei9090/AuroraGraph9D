# AuroraGraph9D

9D Ingestion with Metabolic Filtering and Deterministic Reasoning.

## Setup

1. Install `uv`: [https://github.com/astral-sh/uv](https://github.com/astral-sh/uv)
2. Install dependencies:
   ```bash
   uv sync
   ```

## Usage

### Ingest a file
```bash
uv run src/main.py ingest <filepath>
```

### Query the graph
```bash
uv run src/main.py query <your question>
```

## Features
- **Metabolic Filtering**: Processes only the most information-dense units.
- **9D Synapses**: Maps logic across 9 dimensions (Subject, Relation, Object, Context, Source, Time, Content Pointer, Scope, Semantic Identity).
- **Deterministic Reasoning**: Walks the neural paths to provide evidence-backed answers.
