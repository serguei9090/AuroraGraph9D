import ollama

from auragraph.providers.llm.base import BaseLLMProvider


class OllamaProvider(BaseLLMProvider):
    """
    Ollama implementation for local, secure LLM reasoning.
    """

    def __init__(self, model_name: str):
        self.model_name = model_name

    def generate(self, prompt: str, system_prompt: str, stream: bool = False):
        """
        Generates text using the local Ollama instance.
        """
        if stream:
            return self._generate_stream(prompt, system_prompt)
        else:
            return self._generate_sync(prompt, system_prompt)

    def _generate_sync(self, prompt: str, system_prompt: str) -> str:
        resp = ollama.generate(model=self.model_name, prompt=prompt, system=system_prompt, stream=False)
        return resp["response"]

    def _generate_stream(self, prompt: str, system_prompt: str):
        """
        Generator yielding text chunks for streaming UIs.
        """
        resp = ollama.generate(model=self.model_name, prompt=prompt, system=system_prompt, stream=True)
        for chunk in resp:
            yield chunk["response"]
