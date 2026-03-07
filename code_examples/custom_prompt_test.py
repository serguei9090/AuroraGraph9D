import os
import sys
from pathlib import Path

# Fix Windows Unicode Encode Errors early
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# Ensure we're importing the local source, not the installed package (if testing)
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from auragraph import AuroraGraphEngine  # noqa: E402
from auragraph.db.kuzu import KuzuDB  # noqa: E402

# Configuration
DB_PATH = "./auragraph_graph"

# 1. Provide your own System Prompt
my_system_prompt = "You are an extremely concise, highly creative AI."

# 2. Provide your own RAG prompt
# Ensure you use {query} and {evidence} so the engine can insert the retrieved data!
my_prompt = """
The user asked: {query}

Use this context to answer:
{evidence}

Please ignore Task 1 and Task 2. Just write me an elegant Haiku about the answer.
"""

def main():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}. Please run ingest_knowledge.py first.")
        return

    # Initialize Engine
    engine = AuroraGraphEngine(db=KuzuDB(DB_PATH))

    query = "Why should we use OpenVPN on EC2 instances?"

    print("--- STANDARD AUDIT PROMPT ---")
    standard_result = engine.query(query, stream=False)
    print(standard_result["response"])
    print("\n\n")

    print("--- CUSTOM HAIKU PROMPT ---")
    # Execute query using your own custom RAG instructions!
    custom_result = engine.query(
        query,
        stream=False,
        custom_system_prompt=my_system_prompt,
        custom_prompt=my_prompt
    )
    print(custom_result["response"])

if __name__ == "__main__":
    main()
