import ollama

from auragraph.providers.llm.base import BaseLLMProvider


class OllamaProvider(BaseLLMProvider):
    """
    Ollama implementation for local, secure LLM reasoning.
    """

    def __init__(self, model_name: str):
        self.model_name = model_name
        try:
            # Quick check if Ollama is running and has the model
            # This is non-blocking but ensures we don't hang later
            ollama.show(model_name)
        except Exception as e:
            print(f"[!] Ollama Model Warning: Could not find or access '{model_name}'.")
            print(f"    Error: {e}")
            print(
                "    Make sure Ollama is running (`ollama serve`) and the model is pulled (`ollama pull {model_name}`)."
            )

    def generate(self, prompt: str, system_prompt: str, stream: bool = False):
        """
        Generates text using the local Ollama instance.
        """
        try:
            if stream:
                return self._generate_stream(prompt, system_prompt)
            else:
                return self._generate_sync(prompt, system_prompt)
        except Exception as e:
            return f"Error connecting to LLM: {e}"

    def _generate_sync(self, prompt: str, system_prompt: str) -> str:
        resp = ollama.generate(model=self.model_name, prompt=prompt, system=system_prompt, stream=False)
        return resp["response"]

    def _generate_stream(self, prompt: str, system_prompt: str):
        """
        Generator yielding text chunks for streaming UIs.
        """
        try:
            resp = ollama.generate(model=self.model_name, prompt=prompt, system=system_prompt, stream=True)
            for chunk in resp:
                yield chunk["response"]
        except Exception as e:
            yield f"\n[LLM Stream Error]: {e}"
