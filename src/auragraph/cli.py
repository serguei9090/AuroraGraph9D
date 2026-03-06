"""
auragraph.cli
=============
Command-line interface entry point for the AuroraGraph engine.

Usage:
    auragraph ingest /path/to/docs
    auragraph query "Your question here"
"""

import sys


def main():
    """Main entry point dispatched by the 'auragraph' CLI command."""
    from auragraph.core.engine import AuroraGraphEngine

    if len(sys.argv) < 2:
        print("Usage: auragraph <ingest|query> [args...]")
        sys.exit(1)

    command = sys.argv[1]
    engine = AuroraGraphEngine()

    if command == "ingest":
        if len(sys.argv) < 3:
            print("Usage: auragraph ingest <path>")
            sys.exit(1)
        engine.ingest(sys.argv[2])
    elif command == "query":
        if len(sys.argv) < 3:
            print("Usage: auragraph query <question>")
            sys.exit(1)
        question = " ".join(sys.argv[2:])
        engine.query(question)
    else:
        print(f"Unknown command: {command}")
        print("Available commands: ingest, query")
        sys.exit(1)


if __name__ == "__main__":
    main()
