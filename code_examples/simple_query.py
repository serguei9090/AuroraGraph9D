"""
Simple Query Example for AuroraGraph.
=====================================
Demonstrates how to load an existing Kùzu database and ask a question.
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

# Add src to path if running from local dev
sys.path.append(str(Path(__file__).parent.parent / "src"))

from auragraph import AuroraGraphEngine  # noqa: E402
from auragraph.db.kuzu import KuzuDB  # noqa: E402
from auragraph.providers.embeddings.fastembed_provider import FastEmbedProvider  # noqa: E402


def main():
    load_dotenv()

    # Path to your Kùzu database
    db_path = Path("code_examples/auragraph_graph")

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        print("Please run 'uv run python code_examples/ingest_knowledge.py' first.")
        return

    print(f"Connecting to database at {db_path}...")

    # Initialize Engine
    # We use KuzuDB and FastEmbedProvider (defaulting to CPU for compatibility)
    engine = AuroraGraphEngine(
        db=KuzuDB(str(db_path)),
        embedder=FastEmbedProvider(device="cpu")
    )

    # Get query from CLI or use default
    query_text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "What is the AWS Shared Responsibility Model?"

    print(f"\nQuerying: '{query_text}'...")
    print("-" * 50)

    # Run prediction (streams response to console by default if no stream=False is passed)
    # But here we'll use prediction to see structured data
    result = engine.predict(query_text)

    print(f"\nResponse:\n{result['response']}")

    print("\n" + "-" * 50)
    print(f"Stats: {result['retrieval_ms']:.2f}ms retrieval | {result['generation_ms']:.2f}ms generation")

    if result.get("sources"):
        print("\nSources:")
        for source in result["sources"]:
            print(f"- {source['filename']} (Page {source.get('page', 'N/A')})")

if __name__ == "__main__":
    main()
