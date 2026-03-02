"""
AuroraGraph9D — LLM-as-a-Judge Evaluation Engine.

Uses a local Ollama model to grade system outputs on the RAG Triad:
  1. Context Relevance  — Did FTS5 pull the right paragraphs?
  2. Faithfulness        — Is the answer grounded in the retrieved context?
  3. Answer Relevance    — Does the answer address the specific question?

Each metric is scored 0.0 → 1.0 with a written justification.
"""

import json
import re

import ollama

# The model used as a judge — intentionally different from the generator
# to avoid self-evaluation bias. Switch to a stronger model if available.
JUDGE_MODEL = "llama3.1:8b"


def _ask_judge(prompt: str) -> dict:
    """Send a structured prompt to the judge LLM and parse the JSON result."""
    resp = ollama.generate(
        model=JUDGE_MODEL,
        prompt=prompt,
        system=(
            "You are a strict AI evaluation judge. Respond ONLY with valid "
            "JSON matching the requested schema. No markdown, no commentary."
        ),
        stream=False,
    )
    raw = resp["response"].strip()

    # Attempt to extract JSON from the response
    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    # Fallback if parsing fails
    return {"score": 0.0, "reason": f"Judge returned unparseable output: {raw[:200]}"}


# ─── Metric 1: Context Relevance ─────────────────────────────────────────────

def score_context_relevance(query: str, context: list[str]) -> dict:
    """
    Grades whether the retrieved context is relevant to the user query.
    Score: 0.0 (completely irrelevant) → 1.0 (perfectly relevant).
    """
    context_text = "\n---\n".join(context) if context else "[NO CONTEXT RETRIEVED]"
    prompt = f"""
Evaluate whether the following RETRIEVED CONTEXT is relevant to the USER QUERY.

USER QUERY: {query}

RETRIEVED CONTEXT:
{context_text}

Scoring Guide:
- 1.0: Every piece of context directly addresses the query topic.
- 0.7: Most context is relevant, a few off-topic pieces.
- 0.4: Some context is relevant, but significant noise.
- 0.1: Almost none of the context is relevant.
- 0.0: No context retrieved, or entirely off-topic.

Respond ONLY with JSON:
{{"score": <float 0.0-1.0>, "reason": "<one-line justification>"}}
"""
    return _ask_judge(prompt)


# ─── Metric 2: Faithfulness (Groundedness) ────────────────────────────────────

def score_faithfulness(response: str, context: list[str]) -> dict:
    """
    Grades whether the generated answer is strictly grounded in the context.
    Detects hallucinations — facts in the answer NOT present in context.
    Score: 0.0 (pure hallucination) → 1.0 (fully grounded).
    """
    context_text = "\n---\n".join(context) if context else "[NO CONTEXT]"
    prompt = f"""
Evaluate whether every claim in the GENERATED ANSWER is supported by the CONTEXT.

GENERATED ANSWER:
{response}

CONTEXT (the only source of truth):
{context_text}

Scoring Guide:
- 1.0: Every single fact and claim in the answer appears in the context.
- 0.7: Most claims are grounded, but 1-2 minor details are unsupported.
- 0.4: Several claims are not found in the context.
- 0.1: The answer contains mostly fabricated information.
- 0.0: The answer is entirely made up with no basis in the context.

IMPORTANT: If the answer correctly states "no information found" when the
context is empty or irrelevant, score it 1.0 for faithfulness.

Respond ONLY with JSON:
{{"score": <float 0.0-1.0>, "reason": "<one-line justification>"}}
"""
    return _ask_judge(prompt)


# ─── Metric 3: Answer Relevance ──────────────────────────────────────────────

def score_answer_relevance(query: str, response: str) -> dict:
    """
    Grades whether the generated answer directly addresses the user query.
    Score: 0.0 (completely off-topic) → 1.0 (perfectly addresses the query).
    """
    prompt = f"""
Evaluate whether the GENERATED ANSWER directly and fully addresses the USER QUERY.

USER QUERY: {query}

GENERATED ANSWER:
{response}

Scoring Guide:
- 1.0: The answer directly and comprehensively addresses the exact question.
- 0.7: The answer mostly addresses the question but misses some aspects.
- 0.4: The answer is partially relevant but goes on tangents.
- 0.1: The answer barely relates to the question.
- 0.0: The answer is completely off-topic.

IMPORTANT: If the query asks about a topic NOT in the documents, and the
answer correctly states that no information was found, score it 1.0.

Respond ONLY with JSON:
{{"score": <float 0.0-1.0>, "reason": "<one-line justification>"}}
"""
    return _ask_judge(prompt)


# ─── Full Evaluation ─────────────────────────────────────────────────────────

def evaluate_prediction(prediction: dict) -> dict:
    """
    Run all three RAG Triad metrics against a single prediction.

    Args:
        prediction: dict with keys {query, context, response}

    Returns:
        dict with scores and an overall weighted average.
    """
    query = prediction["query"]
    context = prediction.get("context", [])
    response = prediction.get("response", "")

    ctx_rel = score_context_relevance(query, context)
    faith = score_faithfulness(response, context)
    ans_rel = score_answer_relevance(query, response)

    # Weighted average: faithfulness is the most critical metric
    overall = round(
        ctx_rel["score"] * 0.30
        + faith["score"] * 0.40
        + ans_rel["score"] * 0.30,
        3,
    )

    return {
        "context_relevance": ctx_rel,
        "faithfulness": faith,
        "answer_relevance": ans_rel,
        "overall_score": overall,
    }
