import time

import ollama

model = "qwen3.5:9b"
print(f"Loading and generating from {model}...")
start = time.time()
try:
    resp = ollama.generate(model=model, prompt="Say hello quickly", stream=True)
    for chunk in resp:
        print(chunk["response"], end="", flush=True)
except Exception as e:
    print(f"\nError: {e}")
print(f"\nDone in {time.time() - start:.2f}s")
