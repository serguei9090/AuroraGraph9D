# Phase 2: Neo4j Cypher Integration

The `auragraph` library now ships with native Neo4j graph database support.

## Why Neo4j?
SQLite FTS5 was incredible for exact 0-hallucination keyword matches, but a flat 2D table cannot map complex multi-document relationships. Neo4j allows us to:
1. Store chunks explicitly connected to their source `(Document)-[:HAS_CHUNK]->(Chunk)`.
2. Visualize the exact topological paths the LLM is traversing.
3. Rapidly prepare for Phase 3: the Information Extraction (IE) pipeline which will inject Subject-Predicate-Object triples inside these chunks.

## How to Test the Neo4j Provider

### 1. Start a Local Neo4j Instance (Docker)
The easiest way to run the enterprise graph database locally is via Docker:

```bash
docker run \
    --name neo4j \
    -p 7474:7474 -p 7687:7687 \
    -d \
    -e NEO4J_AUTH=neo4j/password \
    neo4j:latest
```

### 2. Update `.env` Configuration
Open your `.env` file and change the Database Provider from `sqlite` to `neo4j`:

```env
AURA_DB_PROVIDER="neo4j"
NEO4J_URI="bolt://localhost:7687"
NEO4J_USER="neo4j"
NEO4J_PASSWORD="password"
```

### 3. Re-ingest the Documents
Because Neo4j and SQLite are completely separate datasets, you must re-ingest your documents into the new graph:

```bash
uv run run.py ingest tests/test_docs
```

### 4. Visualize the Graph!
Once ingested, open your browser to **http://localhost:7474**.
Login with:
- User: `neo4j`
- Password: `password`

You can run standard Cypher queries to visually map the relationships the AI is creating! For example:
```cypher
MATCH (n) RETURN n LIMIT 100
```
Then, you can execute standard testing and it will route precisely through the graph structure!

```bash
uv run run.py query "When did the Western Roman Empire fall?"
```
