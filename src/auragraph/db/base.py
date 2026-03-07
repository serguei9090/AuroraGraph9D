from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseGraphDB(ABC):
    """
    Abstract Base Class for graph/vector databases.
    All database providers (SQLite FTS5, Neo4j, NebulaGraph) must
    implement these methods to be queried by the JIT Engine.
    """

    @abstractmethod
    def init_schema(self) -> None:
        """Initializes the database schema (tables, nodes, edges)."""
        pass

    @abstractmethod
    def insert_document(
        self,
        filename: str,
        content: str,
        metadata: Dict[str, Any],
        embedding: List[float] = None,
        triples: List[Dict[str, str]] = None,
    ) -> None:
        """Inserts a chunk of a document into the database, optionally with semantic vectors and extraction triples."""
        pass

    @abstractmethod
    def is_ingested(self, filename: str) -> bool:
        """Checks if a file has already been ingested to prevent duplication."""
        pass

    @abstractmethod
    def delete_document(self, filename: str) -> None:
        """Deletes a document and all its associated chunks/relationships."""
        pass

    @abstractmethod
    def search(
        self,
        query_terms: List[str],
        limit: int,
        snippet_words: int,
        query_embedding: List[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves the most relevant context blocks for the query.
        Returns a list of dictionaries containing 'filename', 'page', and 'text'.
        If query_embedding is provided, it can perform Hybrid Vector + Keyword search.
        """
        pass
