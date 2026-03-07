"""
AuroraGraph9D - Automated Evaluation Suite
===========================================

Runs every test case from golden_dataset.json through AuraGraphJIT.predict(),
evaluates the result with the LLM-as-a-Judge (eval_engine.py), then generates
a ranked scorecard saved as both CSV and a rich console report.

Usage:
    uv run pytest tests/test_auragraph.py -v -s
"""

import csv
import datetime
import json
import os
import sys

import pytest

# Add the current directory to sys.path so we can import eval_engine
sys.path.insert(0, os.path.dirname(__file__))

from eval_engine import evaluate_prediction

REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
RESULTS_CACHE: list[dict] = []

# --- Minimum Passing Thresholds ----------------------------------------------
# We set these to 0.0 initially so the report generates even if the system
# hasn't been tuned yet. Raise these as you improve your data.
MIN_CONTEXT_RELEVANCE = 0.0
MIN_FAITHFULNESS = 0.0
MIN_ANSWER_RELEVANCE = 0.0
MIN_OVERALL = 0.0


# --- Parametrised Test: One Per Golden Dataset Entry -------------------------


def _load_golden():
    """Load test cases for parametrize (called at collection time)."""
    path = os.path.join(os.path.dirname(__file__), "golden_dataset.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.evaluation
@pytest.mark.parametrize(
    "test_case",
    _load_golden(),
    ids=lambda tc: tc["id"],
)
def test_auragraph_evaluation(aura, test_case):
    """
    For each golden test case:
      1. Run AuraGraphJIT.predict()
      2. Grade with the LLM-as-a-Judge on 3 metrics
      3. Assert minimum thresholds
      4. Store results for the final report
    """
    tc_id = test_case["id"]
    query = test_case["query"]
    category = test_case["category"]

    print("-" * 70)
    print(f"  TEST {tc_id} [{category}]")
    print(f"  Query: {query}")
    print("-" * 70)

    # -- Step 1: Run the system --------------------------------------------
    prediction = aura.predict(query)

    num_contexts = len(prediction["context"])
    t_retrieval = prediction["retrieval_ms"]
    t_generation = prediction["generation_ms"]
    print(f"  [AURORA] {num_contexts} blocks | Retrieval: {t_retrieval:.1f}ms | LLM Gen: {t_generation / 1000:.1f}s")

    # -- Step 2: Grade with LLM-as-a-Judge ---------------------------------
    scores = evaluate_prediction(prediction)
    t_judging = scores["judge_ms"]

    ctx_score = scores["context_relevance"]["score"]
    faith_score = scores["faithfulness"]["score"]
    ans_score = scores["answer_relevance"]["score"]
    overall = scores["overall_score"]

    print(f"  [SCORES] Judging Time: {t_judging / 1000:.1f}s")
    ctx_r = scores["context_relevance"]["reason"]
    fth_r = scores["faithfulness"]["reason"]
    ans_r = scores["answer_relevance"]["reason"]
    print(f"    Ctx Rel: {ctx_score:.2f} ({ctx_r})")
    print(f"    Faith  : {faith_score:.2f} ({fth_r})")
    print(f"    Ans Rel: {ans_score:.2f} ({ans_r})")
    print(f"    Overall: {overall:.3f}")

    # -- Step 3: Cache result for final report -----------------------------
    RESULTS_CACHE.append(
        {
            "id": tc_id,
            "category": category,
            "query": query,
            "num_contexts": num_contexts,
            "t_retrieval_ms": t_retrieval,
            "t_generation_ms": t_generation,
            "t_judging_ms": t_judging,
            "context_relevance": ctx_score,
            "faithfulness": faith_score,
            "answer_relevance": ans_score,
            "overall": overall,
            "ctx_reason": scores["context_relevance"]["reason"],
            "faith_reason": scores["faithfulness"]["reason"],
            "ans_reason": scores["answer_relevance"]["reason"],
            "response_preview": prediction["response"][:200],
        }
    )

    # -- Step 4: Assertions ------------------------------------------------
    assert ctx_score >= MIN_CONTEXT_RELEVANCE
    assert faith_score >= MIN_FAITHFULNESS
    assert ans_score >= MIN_ANSWER_RELEVANCE
    assert overall >= MIN_OVERALL


# --- Report Generation (runs after all tests) --------------------------------


@pytest.fixture(scope="session", autouse=True)
def generate_report(request):
    """After all tests finish, generate a CSV + console scorecard."""

    def _write():
        if not RESULTS_CACHE:
            return

        os.makedirs(REPORT_DIR, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = os.path.join(REPORT_DIR, f"eval_{timestamp}.csv")

        # --- CSV Report ----------------------------------------------------
        fieldnames = [
            "id",
            "category",
            "query",
            "num_contexts",
            "t_retrieval_ms",
            "t_generation_ms",
            "t_judging_ms",
            "context_relevance",
            "faithfulness",
            "answer_relevance",
            "overall",
            "ctx_reason",
            "faith_reason",
            "ans_reason",
            "response_preview",
        ]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(RESULTS_CACHE)

        # --- Console Scorecard ---------------------------------------------
        n = len(RESULTS_CACHE)
        avg_ctx = sum(r["context_relevance"] for r in RESULTS_CACHE) / n
        avg_faith = sum(r["faithfulness"] for r in RESULTS_CACHE) / n
        avg_ans = sum(r["answer_relevance"] for r in RESULTS_CACHE) / n
        avg_overall = sum(r["overall"] for r in RESULTS_CACHE) / n
        avg_t_ret = sum(r["t_retrieval_ms"] for r in RESULTS_CACHE) / n
        avg_t_gen = sum(r["t_generation_ms"] for r in RESULTS_CACHE) / n
        avg_t_jud = sum(r["t_judging_ms"] for r in RESULTS_CACHE) / n
        passed = sum(1 for r in RESULTS_CACHE if r["overall"] >= MIN_OVERALL)

        print("\n")
        print("=" * 70)
        print("  AURORAGRAPH 9D - EVALUATION SCORECARD")
        print("=" * 70)
        print(f"  Date           : {timestamp}")
        print(f"  Test Cases     : {n}")
        print(f"  Passed         : {passed}/{n} ({passed / n * 100:.0f}%)")
        print("  -------------------------------------")
        print(f"  Avg Retrieval  : {avg_t_ret:.2f} ms")
        print(f"  Avg LLM Gen    : {avg_t_gen / 1000:.2f} s")
        print(f"  Avg Judging    : {avg_t_jud / 1000:.2f} s")
        print("  -------------------------------------")
        print(f"  Ctx Relevance  : {avg_ctx:.3f}")
        print(f"  Faithfulness   : {avg_faith:.3f}")
        print(f"  Ans Relevance  : {avg_ans:.3f}")
        print("  -------------------------------------")
        print(f"  OVERALL SCORE  : {avg_overall:.3f}")
        print("  -------------------------------------")

        # Letter grade
        if avg_overall >= 0.9:
            grade = "A+"
        elif avg_overall >= 0.8:
            grade = "A"
        elif avg_overall >= 0.7:
            grade = "B"
        elif avg_overall >= 0.6:
            grade = "C"
        elif avg_overall >= 0.5:
            grade = "D"
        else:
            grade = "F"

        print(f"  GRADE          : {grade}")
        print("=" * 70)
        print(f"  Report saved   : {csv_path}")
        print("=" * 70)

    request.addfinalizer(_write)
