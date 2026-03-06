import os
import sys

# Ensure the src/ directory is importable from root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from auragraph.core.engine import AuroraGraphEngine


def main():
    # Instantiate the dependency-injected core engine
    # (By default it uses SQLiteFTS5 and OllamaProvider per config.py)
    engine = AuroraGraphEngine()

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python run.py ingest <dir>")
        print("  python run.py query <text>")
    else:
        cmd = sys.argv[1]
        if cmd == "ingest" and len(sys.argv) >= 3:
            engine.ingest_folder(sys.argv[2])
        elif cmd == "query":
            # Pass stream=True to enable real-time typing in the console!
            engine.query(" ".join(sys.argv[2:]), stream=True)
        else:
            print("[!] Missing arguments.")


if __name__ == "__main__":
    main()
