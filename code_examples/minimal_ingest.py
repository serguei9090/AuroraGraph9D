"""
Minimal Ingestion Example for AuroraGraph.
=========================================
A simplified version of the ingestion pipeline.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from auragraph import AuroraGraphEngine  # noqa: E402
from auragraph.db.kuzu import KuzuDB  # noqa: E402
from auragraph.providers.embeddings.fastembed_provider import FastEmbedProvider  # noqa: E402


def main():
    # 1. Config
    db_path = "./code_examples/auragraph_graph"
    source_folder = "./code_examples/knowledge"

    print("Initializing AuroraGraph...")

    # 2. Setup Engine
    # Note: KuzuDB creates the folder if it doesn't exist
    engine = AuroraGraphEngine(
        db=KuzuDB(db_path),
        embedder=FastEmbedProvider(device="cpu")
    )

    # 3. Ingest
    print(f"Ingesting documents from {source_folder}...")

    # engine.ingest_folder is a high-level helper that:
    # - Scans for PDF, TXT, MD
    # - Extracts chunks (metadata, page numbers)
    # - Embeds chunks in batches
    # - Upserts into the graph DB
    engine.ingest_folder(source_folder)

    print("\nIngestion complete!")
    print("You can now query your database using: uv run python code_examples/simple_query.py")

if __name__ == "__main__":
    main()
