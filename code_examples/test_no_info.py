import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from auragraph import AuroraGraphEngine  # noqa: E402
from auragraph.db.kuzu import KuzuDB  # noqa: E402


def test_no_info():
    db_path = Path(__file__).resolve().parent / "auragraph_graph"
    # Create engine with an empty or non-existent path to trigger "no info"
    # Actually, we use the existing one but search for something that definitely isn't there.
    engine = AuroraGraphEngine(db=KuzuDB(str(db_path)))

    print("\n--- TEST: SEARCH FOR NONSENSE ---")
    engine.query("ZXYWVU987654321")
    print("--- TEST END ---")

if __name__ == "__main__":
    test_no_info()
