import os
import re
import time
from typing import Optional

from prometheus_client import Counter, Histogram

from auragraph.core.config import config
from auragraph.db.base import BaseGraphDB
from auragraph.db.sqlite import SQLiteFTS5DB
from auragraph.ingestion.extractor import extract_triples
from auragraph.ingestion.parsers import extract_chunks
from auragraph.providers.embeddings.base import BaseEmbeddingProvider

# LocalEmbeddingProvider imported lazily in __init__
from auragraph.providers.llm.base import BaseLLMProvider

# OllamaProvider imported lazily in __init__

# Define Prometheus Metrics Let's track retrieval and LLM generation
RETRIEVAL_LATENCY = Histogram(
    "auragraph_retrieval_seconds",
    "Time taken for Hybrid Search Retrieval",
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
)
GENERATION_LATENCY = Histogram(
    "auragraph_generation_seconds",
    "Time taken for LLM Synthesis Generation",
    buckets=[0.5, 1.0, 3.0, 5.0, 10.0, 30.0],
)
QUERY_COUNTER = Counter("auragraph_queries_total", "Total engine queries executed")


class AuroraGraphEngine:
    """
    The central orchestrator for the AuroraGraph Knowledge Graph.
    Uses Dependency Injection so the Database and LLM can be swapped
    without changing the core retrieval and reasoning logic.
    """

    def __init__(
        self,
        db: Optional[BaseGraphDB] = None,
        llm: Optional[BaseLLMProvider] = None,
        embedder: Optional[BaseEmbeddingProvider] = None,
    ):
        if db:
            self.db = db
        else:
            if config.AURA_DB_PROVIDER == "neo4j":
                from auragraph.db.neo4j import Neo4jDB

                self.db = Neo4jDB(config.NEO4J_URI, config.NEO4J_USER, config.NEO4J_PASSWORD)
            elif config.AURA_DB_PROVIDER == "kuzu":
                from auragraph.db.kuzu import KuzuDB

                self.db = KuzuDB(config.KUZU_DB_PATH)
            else:
                self.db = SQLiteFTS5DB(config.DEFAULT_DB_PATH)

        if llm:
            self.llm = llm
        else:
            try:
                from auragraph.providers.llm.ollama import OllamaProvider

                self.llm = OllamaProvider(config.AURA_MODEL)
            except ImportError:
                self.llm = None

        # Instantiate embedder only if desired (defaults to FastEmbed, fallback to Local MiniLM)
        self.embedder = embedder
        if not self.embedder:
            try:
                # 1. Try FastEmbed (Fastest & Officially Supported)
                from auragraph.providers.embeddings.fastembed_provider import FastEmbedProvider

                self.embedder = FastEmbedProvider()
            except ImportError:
                self.embedder = None

    def close(self) -> None:
        """Explicitly release resources (DB connections, etc.)."""
        if hasattr(self, "db") and hasattr(self.db, "close"):
            self.db.close()

    def ingest_folder(self, folder_path: str):
        """
        Scans a folder and ingests files into the provided GraphDB.
        """
        if not os.path.exists(folder_path):
            return

        files = [
            os.path.join(r, f)
            for r, _, fs in os.walk(folder_path)
            for f in fs
            if f.lower().endswith((".pdf", ".txt", ".md"))
        ]
        start_time = time.time()
        new_files = 0
        skipped_files = 0

        for filepath in files:
            fname = os.path.basename(filepath)

            if self.db.is_ingested(fname):
                skipped_files += 1
                continue

            chunks = extract_chunks(filepath)
            for chunk in chunks:
                # 1. Calculate Vector Embedding
                embedding = None
                if self.embedder:
                    embedding = self.embedder.embed_text(chunk["content"])

                # 2. Extract Triples (Synapse routing)
                triples = []
                try:
                    triples = extract_triples(chunk["content"])
                except Exception:
                    pass

                # 3. Insert Hybrid Data
                self.db.insert_document(
                    filename=chunk["filename"],
                    content=chunk["content"],
                    metadata=chunk["metadata"],
                    embedding=embedding,
                    triples=triples,
                )

            if chunks:
                new_files += 1

        return {"processed": new_files, "skipped": skipped_files, "time_taken_sec": round(time.time() - start_time, 2)}

    def query(
        self,
        user_query: str,
        stream: bool = True,
        custom_prompt: Optional[str] = None,
        custom_system_prompt: Optional[str] = None,
    ) -> dict:
        """
        Legacy wrapper around predict. Please use predict() for programmatic response.
        """
        return self.predict(
            user_query,
            stream=stream,
            custom_prompt=custom_prompt,
            custom_system_prompt=custom_system_prompt,
        )

    def predict(
        self,
        user_query: str,
        stream: bool = False,
        custom_prompt: Optional[str] = None,
        custom_system_prompt: Optional[str] = None,
    ) -> dict:
        """
        Programmatic graph traversal and LLM generation.
        If stream is True, 'response' in the dict will be a Python Generator.
        """
        start_retrieval = time.time()

        # Extremely basic stop-word filter (to be replaced by Query Rewriter in Phase 3)
        stop_words = {
            "what",
            "were",
            "done",
            "for",
            "all",
            "time",
            "the",
            "and",
            "how",
            "is",
            "are",
            "was",
            "in",
            "on",
            "to",
            "with",
        }
        terms = [w for w in re.findall(r"\w+", user_query) if w.lower() not in stop_words]

        empty_result = {
            "query": user_query,
            "context": [],
            "response": "",
            "sources": [],
            "retrieval_ms": 0,
            "generation_ms": 0,
        }

        if not terms:
            empty_result["retrieval_ms"] = round((time.time() - start_retrieval) * 1000, 2)
            return empty_result

        # Increment total queries
        QUERY_COUNTER.inc()

        # 1. Query Vector Embedding
        query_embedding = None
        if self.embedder:
            query_embedding = self.embedder.embed_text(user_query)

        # 2. Database Retrieval
        with RETRIEVAL_LATENCY.time():
            results = self.db.search(
                terms,
                config.FTS5_MATCH_LIMIT,
                config.FTS5_SNIPPET_WORDS,
                query_embedding=query_embedding,
            )

        retrieval_ms = (time.time() - start_retrieval) * 1000

        if not results:
            empty_result["retrieval_ms"] = round(retrieval_ms, 2)
            empty_result["response"] = "The provided documents do not contain information relevant to your query."
            return empty_result

        # 2. Evidence Formatting
        evidence_blocks = []
        sources = []
        for res in results:
            evidence_blocks.append(f"SOURCE: {res['filename']} (Page {res['page']})\nTEXT: {res['text']}\n")
            sources.append({"filename": res["filename"], "page": res["page"]})

        full_evidence = "\n".join(evidence_blocks)

        if custom_prompt:
            try:
                prompt = custom_prompt.format(query=user_query, evidence=full_evidence)
            except KeyError:
                # Fallback if the user forgets to include {query} or {evidence} format blocks
                prompt = custom_prompt + f"\n\nQUERY: {user_query}\n\nEVIDENCE:\n{full_evidence}"
        else:
            prompt = f"""
            You are the AuroraGraph Audit AI.

            USER QUERY: {user_query}

            DATABASE EVIDENCE (Keywords are highlighted with ** **):
            {full_evidence}

            TASK 1: Extract the specific improvements, changes, or facts requested.
            TASK 2: Synthesize a clear report. Cite the Source Filename and Page Number.

            CRITICAL RULE: If the evidence does not specifically mention the exact
            technologies or concepts in the user query, you MUST state:
            "The provided documents do not contain information about [Topic]."
            DO NOT hallucinate or substitute technologies.
            """

        sys_prompt = (
            custom_system_prompt
            or "You are a precise technical auditor. Rely STRICTLY on the provided evidence. If it's not in the evidence, say you don't know."
        )

        # 3. LLM Generation
        start_gen = time.time()

        if not self.llm:
            raise ValueError(
                "LLM Provider is not initialized. "
                "Ensure 'ollama' is installed and running, or pass an LLM provider to the engine. "
                "You can install all dependencies with 'uv sync --all-extras'."
            )

        if not stream:
            with GENERATION_LATENCY.time():
                llm_response = self.llm.generate(prompt, sys_prompt, stream=stream)
        else:
            # We can't strictly perfectly measure streaming latency inside context manager without wrapping the generator
            llm_response = self.llm.generate(prompt, sys_prompt, stream=stream)

        if not stream:
            generation_ms = (time.time() - start_gen) * 1000
        else:
            generation_ms = 0  # Streaming time is measured via TTFT during iteration

        return {
            "query": user_query,
            "context": evidence_blocks,
            "response": llm_response,
            "sources": sources,
            "retrieval_ms": round(retrieval_ms, 2),
            "generation_ms": round(generation_ms, 2),
        }
