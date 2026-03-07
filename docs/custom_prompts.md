# Customizing Retrieval Prompts

By default, AuroraGraph enforces a highly structured **Audit Response**. It forces the LLM to process documents linearly and verify its findings across two Tasks. While this creates a 0% hallucination rate, it makes generation naturally slower.

However, an enterprise developer rarely wants the default prompt! You can easily override the prompts using simple string arguments to `engine.query()`.

## 1. Changing the System Prompt

The System Prompt is the instruction layer loaded into the LLM before any specific conversation occurs. By default, AuroraGraph uses:
> *"You are a precise technical auditor. Rely STRICTLY on the provided evidence. If it's not in the evidence, say you don't know."*

To modify this, pass `custom_system_prompt`:

```python
from auragraph import AuroraGraphEngine
from auragraph.db.kuzu import KuzuDB

engine = AuroraGraphEngine(db=KuzuDB("./auragraph_graph"))

my_system_prompt = "You are an extremely concise, highly creative AI."

result = engine.query(
    "Why should we use OpenVPN?", 
    stream=False, 
    custom_system_prompt=my_system_prompt
)
```

## 2. Implementing the RAG Flow (User Prompt)

AuroraGraph operates entirely under the hood. When you run `engine.query()`, it traverses the Graph Database, maps the Synapses, runs Hybrid BM25 Vectors via FastEmbed, and produces a string format of the evidence.

If you want to write your own `custom_prompt`, you **MUST** include `{query}` and `{evidence}`, so the Engine has a place to inject the context it retrieved!

```python
# Create a Custom Generation Prompt!
my_prompt = """
The user asked: {query}

Use this context to answer:
{evidence}

Please ignore Task 1 and Task 2. Just write me an elegant Haiku about the answer.
"""

result = engine.query(
    "Why should we use OpenVPN on EC2 instances?", 
    stream=False, 
    custom_system_prompt="You are a poet.", 
    custom_prompt=my_prompt
)
```

If the engine determines that the LLM cannot safely format your `{query}` and `{evidence}`, it will safely inject them automatically at the bottom of your prompt to prevent catastrophic prompt poisoning.
