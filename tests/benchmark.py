import sys
import time

import requests

# Change this if running against the docker container or explicitly local
SERVICE_URL = "http://localhost:8000"


def check_health():
    try:
        res = requests.get(f"{SERVICE_URL}/health", timeout=5)
        res.raise_for_status()
        print(f"[OK] Service is healthy: {res.json()}")
        return True
    except Exception as e:
        print(f"[FAIL] Health check failed: {e}")
        return False


def run_benchmark():
    test_cases = [
        {"complexity": "Simple", "query": "What is AuroraGraph?"},
        {"complexity": "Medium", "query": "How does the ingestion process chunk data and filter it?"},
        {
            "complexity": "Complex",
            "query": "Compare the Tri-Modal graph architecture (SQLite, Neo4j, Kuzu) with the recursive chunking algorithm. Explain how they interact.",
        },
    ]

    print("\n" + "=" * 50)
    print("AURORAGRAPH Graph - PERFORMANCE BENCHMARK")
    print("=" * 50)

    results = []

    for tc in test_cases:
        print(f"\n[*] Running {tc['complexity']} Query: '{tc['query']}'...")
        start_time = time.time()

        try:
            response = requests.post(f"{SERVICE_URL}/query", json={"query": tc["query"], "stream": False}, timeout=120)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"    [!] Error: {e}")
            continue

        total_time_ms = (time.time() - start_time) * 1000
        data = response.json()

        retrieval_ms = data.get("retrieval_ms", 0)
        generation_ms = data.get("generation_ms", 0)

        print(f"    - Retrieval Time: {retrieval_ms:.2f} ms")
        print(f"    - LLM Generation: {generation_ms:.2f} ms")
        print(f"    - Total TTFB E2E: {total_time_ms:.2f} ms")

        results.append(
            {
                "complexity": tc["complexity"],
                "query": tc["query"],
                "retrieval_ms": retrieval_ms,
                "generation_ms": generation_ms,
                "total_ms": round(total_time_ms, 2),
            }
        )

    print("\n" + "=" * 50)
    print("BENCHMARK REPORT")
    print("=" * 50)

    # Save report to markdown
    report_md = "# AuroraGraph Performance Benchmark\n\n"
    report_md += "| Complexity | Retrieval (ms) | LLM Generation (ms) | Total E2E (ms) |\n"
    report_md += "|---|---|---|---|\n"

    for r in results:
        report_md += f"| {r['complexity']} | {r['retrieval_ms']} | {r['generation_ms']} | {r['total_ms']} |\n"

    with open("benchmark_report.md", "w") as f:
        f.write(report_md)

    print("Saved benchmark results to benchmark_report.md")


if __name__ == "__main__":
    print(f"Connecting to AuroraGraph Service at {SERVICE_URL}...")
    if check_health():
        run_benchmark()
    else:
        print(
            "Please ensure you have started the server using `uv run uvicorn src.auragraph.app:app --reload` or `docker compose up`"
        )
        sys.exit(1)
