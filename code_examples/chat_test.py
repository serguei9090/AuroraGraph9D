import os
import sys
import time
from pathlib import Path

from colorama import Fore, Style, init

init()  # Initialize colorama for Windows

# Add the parent 'src' directory to avoid dependency issues if not installed
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

# Force utf-8 stdout globally if possible to avoid charmap crashes from fastembed
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

try:
    from dotenv import load_dotenv  # noqa: E402

    from auragraph import AuroraGraphEngine  # noqa: E402
    from auragraph.db.kuzu import KuzuDB  # noqa: E402
except ImportError as e:
    print(f"Error: {e}. Please run 'uv sync --all-extras' in the root directory first.")
    sys.exit(1)

# Load parent .env if exists
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# As requested, we use the specific model available in your local environment.
# Using llama3.1:8b as default as asked, but overriding from .env takes precedence.
LLM_MODEL = os.getenv("AURA_MODEL", "llama3.1:8b")
AUDIT_TITLE = "AURORAGRAPH Graph AUDIT"



class ChatTerminal:
    """A chat terminal that uses AuroraGraph for answering based on ingested knowledge."""

    def __init__(self):
        # Shared Graph with the ingestion script
        db_path = Path(__file__).resolve().parent / "auragraph_graph"
        print(f"[*] Initializing Chat Terminal (LLM: {LLM_MODEL})...")
        print(f"[*] Graph Storage: {db_path}")

        start_init = time.time()
        try:
            self.engine = AuroraGraphEngine(db=KuzuDB(str(db_path)))
            print(f"[*] Engine initialization took {(time.time() - start_init)*1000:.2f}ms")
        except Exception as e:
            print(f"[!] Critical error during initialization: {e}")
            sys.exit(1)

    def query(self, text: str) -> str:
        """Programmatic entry point for queries."""
        print(Fore.CYAN + f"\n[*] Querying Graph Index for: '{text}'..." + Style.RESET_ALL)

        start_query = time.time()
        try:
            # The engine is now silent. We handle the display here.
            prediction = self.engine.query(text, stream=True)

            # --- Explicitly show what the Graph DB found (The Evidence) ---
            sources = prediction.get("sources", [])
            print(Fore.MAGENTA + "\n[GRAPH DB EVIDENCE RETRIEVED]" + Style.RESET_ALL)
            if sources:
                for idx, src in enumerate(sources):
                    print(Fore.GREEN + f"  → Source {idx+1}: {src['filename']} (Page {src.get('page', 'N/A')})" + Style.RESET_ALL)
            else:
                print(Fore.RED + "  → No relevant context found in the graph database." + Style.RESET_ALL)


            if not isinstance(prediction["response"], str):
                print(Fore.YELLOW + "\n" + "=" * 80)

                # Attempt to set stdout to UTF-8 to prevent 'charmap' Windows errors
                try:
                    sys.stdout.reconfigure(encoding='utf-8')
                except Exception:
                    pass

                print(f"{AUDIT_TITLE} (Waiting for LLM to synthesize...)" + Style.RESET_ALL, end="\r", flush=True)

                start_stream = time.time()
                generator = iter(prediction["response"])

                try:
                    first_chunk = next(generator)

                    print(Fore.YELLOW + AUDIT_TITLE + " " * 35)
                    print("=" * 80)

                    # LLM Generation in Bright Yellow so it's clearly distinct from the Green DB evidence
                    try:
                        print(first_chunk, end="", flush=True)
                    except UnicodeEncodeError:
                        print(first_chunk.encode(sys.stdout.encoding, errors='replace').decode(sys.stdout.encoding), end="", flush=True)

                    for chunk in generator:
                        try:
                            print(chunk, end="", flush=True)
                        except UnicodeEncodeError:
                            print(chunk.encode(sys.stdout.encoding, errors='replace').decode(sys.stdout.encoding), end="", flush=True)

                except StopIteration:
                    print(Fore.YELLOW + AUDIT_TITLE)
                    print("=" * 80)
                    print("[No response generated]" + Style.RESET_ALL)
                except Exception as stream_err:
                    print(Fore.RED + f"\n[!] Model generation stream interrupted: {stream_err}" + Style.RESET_ALL)

                stream_duration = (time.time() - start_stream) * 1000
                prediction["generation_ms"] = round(stream_duration, 2)
                print("\n" + "=" * 80 + Style.RESET_ALL)
            else:
                print(Fore.YELLOW + "\n" + "=" * 80)
                print(AUDIT_TITLE)
                print("=" * 80)
                print(prediction["response"])
                print("=" * 80 + Style.RESET_ALL)

            print(Fore.BLUE + f"[*] Stats: Retrieval: {prediction['retrieval_ms']}ms | Generation: {prediction['generation_ms']}ms" + Style.RESET_ALL)

        except Exception as e:
            print(f"[!] Query failed: {e}")

        end_query = time.time()
        print(f"[*] Total query turnaround time: {(end_query - start_query)*1000:.2f}ms")

        return ""

    def interactive_loop(self):
        """Starts an interactive loop for user input."""
        print("\n--- AuroraGraph Chat Ready ---")
        print("Type 'exit' to quit. Type 'query <text>' for a single query.")

        while True:
            # Removed emojis for Windows terminal compatibility
            prompt = input("\nYou: ")
            if prompt.lower() in ["exit", "quit", "q"]:
                print("Goodbye!")
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

    try:
        # Check if a query was passed in as a command-line argument for programmatic testing
        if len(sys.argv) > 1:
            query_text = " ".join(sys.argv[1:])
            terminal.query(query_text)
            # Explicitly close and exit to prevent "staying there forever" on Windows
            terminal.engine.close()
            sys.exit(0)
        else:
            # Otherwise start interactive loop
            terminal.interactive_loop()
            terminal.engine.close()
            sys.exit(0)
    except KeyboardInterrupt:
        print("\n[*] Interrupted by user. Exiting...")
        if hasattr(terminal, "engine"):
            terminal.engine.close()
        sys.exit(0)


if __name__ == "__main__":
    main()
