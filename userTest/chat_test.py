import os
import sys
from pathlib import Path

# Add the parent 'src' directory to avoid dependency issues if not installed
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

try:
    from dotenv import load_dotenv

    from auragraph import AuroraGraphEngine
    from auragraph.db.kuzu import KuzuDB
except ImportError as e:
    print(f"Error: {e}. Please run 'uv sync' in the root directory first.")
    sys.exit(1)

# Load parent .env if exists
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# As requested, we use the specific model available in your local environment.
LLM_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:9b")


class ChatTerminal:
    """A chat terminal that uses AuroraGraph for answering based on ingested knowledge."""

    def __init__(self):
        # Shared Graph with the ingestion script
        db_path = Path(__file__).resolve().parent / "auragraph_graph"
        print(f"🧠 Initializing Chat Terminal (LLM: {LLM_MODEL})...")
        print(f"📂 Graph Storage: {db_path}")
        self.engine = AuroraGraphEngine(db=KuzuDB(str(db_path)))

    def query(self, text: str) -> str:
        """Programmatic entry point for queries."""
        print(f"\n[QUERY]: {text}")
        response = self.engine.query(text)
        print(f"\n[RESPONSE]: {response}")
        return response

    def interactive_loop(self):
        """Starts an interactive loop for user input."""
        print("\n--- AuroraGraph 10D Chat Ready ---")
        print("Type 'exit' to quit. Type 'query <text>' for a single query.")

        while True:
            prompt = input("\n👤 You: ")
            if prompt.lower() in ["exit", "quit", "q"]:
                print("Goodbye! 🌌")
                break

            if not prompt.strip():
                continue

            # Simple check for 'query' keyword or just direct query
            if prompt.lower().startswith("query "):
                self.query(prompt[6:])
            else:
                self.query(prompt)


def main():
    terminal = ChatTerminal()

    # Check if a query was passed in as a command-line argument for programmatic testing
    if len(sys.argv) > 1:
        query_text = " ".join(sys.argv[1:])
        terminal.query(query_text)
    else:
        # Otherwise start interactive loop
        terminal.interactive_loop()


if __name__ == "__main__":
    main()
