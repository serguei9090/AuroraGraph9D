from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    """
    Abstract Base Class for LLM Providers.
    Any custom language model backends (Ollama, OpenAI, Anthropic, vLLM)
    must implement this interface.
    """

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str, stream: bool = False) -> str:
        """
        Generates a response given a user prompt and a system prompt.
        If stream=True, this should yield strings (chunks).
        If stream=False, this returns the full string at once.
        """
        pass
