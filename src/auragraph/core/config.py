import os

from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()


class AuroraConfig:
    """Centralized configuration loading for AuroraGraph."""

    # LLM Settings
    AURA_MODEL = os.getenv("AURA_MODEL", "llama3.1:8b")

    # Context Settings
    AURA_CONTEXT_WINDOW = int(os.getenv("AURA_CONTEXT_WINDOW", 256000))

    # Database / FTS5 Settings
    FTS5_MATCH_LIMIT = int(os.getenv("FTS5_MATCH_LIMIT", 25))
    FTS5_SNIPPET_WORDS = int(os.getenv("FTS5_SNIPPET_WORDS", 200))

    # Storage Paths & Provider Settings
    DEFAULT_DB_PATH = os.getenv("AURA_DB_PATH", "auragraph_jit.db")
    KUZU_DB_PATH = os.getenv("KUZU_DB_PATH", "./auragraph_graph")
    AURA_DB_PROVIDER = os.getenv("AURA_DB_PROVIDER", "sqlite").lower()

    # Device Selection: "auto" (default) | "cpu" | "cuda" | "mps"
    # "auto" will try CUDA → MPS → CPU in order, using the best available.
    AURA_DEVICE = os.getenv("AURA_DEVICE", "auto").lower()

    # Parallel ingestion worker count (number of files processed concurrently).
    # "0" means use all available CPU cores.
    AURA_CONCURRENCY = int(os.getenv("AURA_CONCURRENCY", 4))

    # Neo4j Settings (Used only if AURA_DB_PROVIDER='neo4j')
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")


config = AuroraConfig()
