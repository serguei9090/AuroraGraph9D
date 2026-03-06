from abc import ABC, abstractmethod
from typing import List


class BaseEmbeddingProvider(ABC):
    """
    Abstract Base Class for Text Embeddings.
    Allows for interchangeable providers like SentenceTransformers, OpenAI, etc.
    """

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Embeds a single string into a vector of floats."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embeds a list of strings into a list of vectors."""
        pass
