# Configuration Guide

AuroraGraph provides a highly customizable, dependency-injected RAG environment. All configuration can be driven securely via environment variables or explicitly via code injection.

## 1. Environment Variables (`.env`)

You can place a `.env` file at the root of your application, and AuroraGraph will automatically consume it if it is loaded into the OS environment. Here are all supported configuration flags:

### Model & Embedding Settings
| Variable | Default | Description |
|:---|:---|:---|
| `AURA_MODEL` | `llama3.1:8b` | The local Ollama LLM model used for the final Generation step. |
| `AURA_DEVICE` | `auto` | Choose what hardware FastEmbed uses. Options: `auto`, `cpu`, `cuda`, `mps`. |
| `AURA_CONTEXT_WINDOW` | `256000` | The assumed max context window for the embedding/graph operations. |

### Database Routing
| Variable | Default | Description |
|:---|:---|:---|
| `AURA_DB_PROVIDER` | `sqlite` | The specific backend you want to use. Options: `sqlite`, `kuzu`, `neo4j`. |
| `KUZU_DB_PATH` | `./auragraph_graph` | The directory where the Kùzu Graph Database will persist its binary graph. |
| `DEFAULT_DB_PATH` | `database.db` | The path for the fallback SQLite store if `sqlite` is chosen. |

### Enterprise Neo4j Cluster Configuration
| Variable | Default | Description |
|:---|:---|:---|
| `NEO4J_URI` | `bolt://localhost:7687` | URI connection string to the local or cloud Neo4j instance. |
| `NEO4J_USER` | `neo4j` | The authentication username. |
| `NEO4J_PASSWORD`| `password` | The authentication password. |

### Search Retrieval Tuning
| Variable | Default | Description |
|:---|:---|:---|
| `FTS5_MATCH_LIMIT` | `25` | The maximum number of graph semantic context chunks to return to the LLM. |
| `FTS5_SNIPPET_WORDS` | `200` | The maximum token/word length of the targeted snippet extractions. |

---

## 2. Dynamic Initialization (In Code)

If you are deploying AuroraGraph as a Library in a cloud application (like a FastAPI service or a Next.js serverless backend), you probably don't want to use `.env` files. 

You can bypass the `.env` settings entirely using standard Python **Dependency Injection**. Note that all three core components (Database, Vector Embedder, Language Model) take `Base` classes, meaning you can construct and inject *your own entirely custom providers*!

```python
from auragraph import AuroraGraphEngine
from auragraph.db.kuzu import KuzuDB
from auragraph.providers.embeddings.fastembed_provider import FastEmbedProvider
from auragraph.providers.llm.ollama import OllamaProvider

# 1. Initialize custom providers manually
my_db = KuzuDB(db_path="/tmp/custom_embedded_graph")
my_embedder = FastEmbedProvider()  # Runs automatically based on hardware
my_llm = OllamaProvider(model_name="deepseek-r1:8b") 

# 2. Inject them into the engine directly
engine = AuroraGraphEngine(
    db=my_db,
    embedder=my_embedder,
    llm=my_llm
)
```

With this capability, developers can easily swap `OllamaProvider` with a hypothetical `OpenAIProvider` or `AnthropicProvider` without changing any of the mathematical logic or retrieval pipelines!
