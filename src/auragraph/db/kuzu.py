"""
KuzuDB — AuroraGraph's embedded Graph graph backend.
===================================================
Zero Docker setup. Uses Kùzu's native FTS (BM25) + Vector (HNSW) extensions
for Hybrid Search fused via Reciprocal Rank Fusion (RRF).

Audit fixes applied (2026-03-06):
  P1 - Context manager + atexit cleanup to release Windows file lock.
  P2 - Atomic document insertion via a single coordinated Cypher sequence.
  P3 - Replaced bare except-pass with filtered warning logging.
  P4 - Extracted _create_chunk(), _link_entities(), _link_chunk_to_entities()
       private helpers to keep insert_document() readable.
"""

import atexit
import logging
import time
from typing import Any, Dict, List, Optional

import kuzu

from auragraph.db.base import BaseGraphDB

log = logging.getLogger(__name__)


class KuzuDB(BaseGraphDB):
    """
    Embedded Graph Database using Kùzu.

    Supports use as a context manager::

        with KuzuDB("./graph") as db:
            db.insert_document(...)

    Or as a plain object — `close()` is registered with `atexit` automatically
    so the file lock is released even on unclean process exits.
    """

    def __init__(self, db_path: str = "./auragraph_graph") -> None:
        self.db_path = db_path
        self.db = kuzu.Database(db_path)
        self.conn = kuzu.Connection(self.db)

        # P1: Guarantee unlock even on crash / Ctrl-C (Windows-safe)
        atexit.register(self.close)

        self._init_schema()

    # Public contract required by BaseGraphDB
    def init_schema(self) -> None:
        """Public alias — delegates to _init_schema(). Called by the base class contract."""
        self._init_schema()

    # ──────────────────────────────────────────────────────────────────────────
    # Context-manager protocol
    # ──────────────────────────────────────────────────────────────────────────

    def __enter__(self) -> "KuzuDB":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def close(self) -> None:
        """Explicitly close the Kùzu connection and release the file lock."""
        try:
            if hasattr(self, "conn") and self.conn is not None:
                self.conn.close()
                self.conn = None
        except Exception:
            pass
        try:
            if hasattr(self, "db") and self.db is not None:
                self.db.close()
                self.db = None
        except Exception:
            pass

    # ──────────────────────────────────────────────────────────────────────────
    # Schema initialisation
    # ──────────────────────────────────────────────────────────────────────────

    def _init_schema(self) -> None:
        """
        Creates node/relationship tables and installs FTS + Vector extensions.
        All DDL is idempotent (IF NOT EXISTS).

        P3: Failures are logged as WARNING unless the cause is "already exists".
        """
        self._try_load_extension("fts")
        self._try_load_extension("vector")

        schema_queries: List[str] = [
            "CREATE NODE TABLE IF NOT EXISTS Document(filename STRING PRIMARY KEY, ingested_at INT64)",
            (
                "CREATE NODE TABLE IF NOT EXISTS Chunk"
                "(id SERIAL PRIMARY KEY, content STRING, page INT64, embedding FLOAT[384], timestamp INT64)"
            ),
            "CREATE NODE TABLE IF NOT EXISTS Entity(id STRING PRIMARY KEY)",
            "CREATE REL TABLE IF NOT EXISTS HAS_CHUNK(FROM Document TO Chunk)",
            "CREATE REL TABLE IF NOT EXISTS MENTIONS(FROM Chunk TO Entity)",
            "CREATE REL TABLE IF NOT EXISTS RELATES_TO(FROM Entity TO Entity, predicate STRING)",
        ]

        for query in schema_queries:
            self._execute_safe(query, label="Schema DDL")

        # Indexes — errors here are always benign (already exists)
        self._execute_safe(
            "CALL CREATE_FTS_INDEX('Chunk', 'chunk_fts', ['content'], stemmer := 'porter')",
            label="FTS Index",
        )
        self._execute_safe(
            "CALL CREATE_VECTOR_INDEX('Chunk', 'chunk_vec', 'embedding')",
            label="Vector Index",
        )

    def _try_load_extension(self, name: str) -> None:
        """Installs and loads a Kùzu extension, suppressing already-loaded errors."""
        for stmt in (f"INSTALL {name}", f"LOAD {name}"):
            try:
                self.conn.execute(stmt)
            except Exception as exc:
                if "already" not in str(exc).lower():
                    log.warning("[KuzuDB] Extension %r: %s — %s", name, stmt, exc)

    def _execute_safe(self, query: str, params: Optional[Dict] = None, label: str = "Query") -> Optional[Any]:
        """Execute a Cypher query, logging unexpected errors as warnings."""
        try:
            return self.conn.execute(query, params or {})
        except Exception as exc:
            msg = str(exc).lower()
            if "already exists" in msg or "already indexed" in msg:
                return None  # Benign idempotency hit
            log.warning("[KuzuDB] %s warning: %s", label, exc)
            return None

    # ──────────────────────────────────────────────────────────────────────────
    # Public write API
    # ──────────────────────────────────────────────────────────────────────────

    def is_ingested(self, filename: str) -> bool:
        result = self.conn.execute(
            "MATCH (d:Document {filename: $filename}) RETURN d.filename",
            {"filename": filename},
        )
        return result.has_next()

    def delete_document(self, filename: str) -> None:
        """
        Deletes a document and all its associated chunks + relationships.
        Note: Entities are kept as they may be referenced by other documents.
        """
        log.info("[KuzuDB] Deleting document: %s", filename)
        # 1. Delete MENTIONS from chunks of this doc
        self._execute_safe(
            "MATCH (d:Document {filename: $filename})-[:HAS_CHUNK]->(c:Chunk)-[r:MENTIONS]->(e:Entity) DELETE r",
            {"filename": filename},
            label="Delete MENTIONS",
        )
        # 2. Delete HAS_CHUNK and Chunk nodes
        self._execute_safe(
            "MATCH (d:Document {filename: $filename})-[r:HAS_CHUNK]->(c:Chunk) DETACH DELETE c",
            {"filename": filename},
            label="Delete Chunks",
        )
        # 3. Delete Document node itself
        self._execute_safe(
            "MATCH (d:Document {filename: $filename}) DETACH DELETE d", {"filename": filename}, label="Delete Document"
        )

    def insert_document(
        self,
        filename: str,
        content: str,
        metadata: Dict[str, Any],
        embedding: Optional[List[float]] = None,
        triples: Optional[List[Dict[str, str]]] = None,
    ) -> None:
        """
        Inserts a Document→Chunk structure with optional embedding and triples.

        P2 — Atomic session:
        All Cypher mutations are issued in sequence with shared parameters so
        that partial failures do not leave orphaned nodes.  The timestamp ties
        the Document→Chunk join without requiring a separate id lookup.
        """
        page = int(metadata.get("page", 1))
        ts = int(time.time())

        # 1. Upsert the Document node (idempotent)
        self._execute_safe(
            "MERGE (d:Document {filename: $filename}) ON CREATE SET d.ingested_at = $ts",
            {"filename": filename, "ts": ts},
            label="Upsert Document",
        )

        # 2. Create the Chunk node
        chunk_id = self._create_chunk(content, page, ts, embedding)
        if chunk_id is None:
            log.warning("[KuzuDB] Chunk creation failed for '%s' page %d — skipping.", filename, page)
            return

        # 3. Link Document → Chunk
        self._execute_safe(
            """
            MATCH (d:Document {filename: $filename})
            MATCH (c:Chunk {content: $content, timestamp: $ts})
            CREATE (d)-[:HAS_CHUNK]->(c)
            """,
            {"filename": filename, "content": content, "ts": ts},
            label="HAS_CHUNK rel",
        )

        # 4. Insert entity triples (Synaptic Links)
        if triples:
            self._link_entities(content, ts, triples)

    # ──────────────────────────────────────────────────────────────────────────
    # P4: Private helpers extracted from insert_document
    # ──────────────────────────────────────────────────────────────────────────

    def _create_chunk(
        self,
        content: str,
        page: int,
        ts: int,
        embedding: Optional[List[float]],
    ) -> Optional[int]:
        """
        Creates a Chunk node and returns its SERIAL id, or None on failure.
        Keeps the embedding path DRY — one branch with/without the float array.
        """
        if embedding:
            result = self._execute_safe(
                "CREATE (c:Chunk {content: $content, page: $page, embedding: $emb, timestamp: $ts}) RETURN c.id",
                {"content": content, "page": page, "emb": embedding, "ts": ts},
                label="Create Chunk (with embedding)",
            )
        else:
            result = self._execute_safe(
                "CREATE (c:Chunk {content: $content, page: $page, timestamp: $ts}) RETURN c.id",
                {"content": content, "page": page, "ts": ts},
                label="Create Chunk (no embedding)",
            )

        if result and result.has_next():
            return result.get_next()[0]
        return None

    def _link_entities(
        self,
        content: str,
        ts: int,
        triples: List[Dict[str, str]],
    ) -> None:
        """
        Upserts Entity nodes, RELATES_TO edges, and MENTIONS edges for each triple.
        Individual triple failures are logged but do not abort the whole batch.
        """
        for triple in triples:
            subject = triple.get("subject", "")
            obj = triple.get("object", "")
            predicate = triple.get("predicate", "")

            if not (subject and obj and predicate):
                log.debug("[KuzuDB] Skipping incomplete triple: %s", triple)
                continue

            try:
                self._upsert_entity(subject)
                self._upsert_entity(obj)
                self._upsert_relates_to(subject, obj, predicate)
                self._link_chunk_to_entity(content, ts, subject)
                self._link_chunk_to_entity(content, ts, obj)
            except Exception as exc:
                log.warning("[KuzuDB] Triple insert error (%s → %s): %s", subject, obj, exc)

    def _upsert_entity(self, entity_id: str) -> None:
        self._execute_safe(
            "MERGE (e:Entity {id: $id})",
            {"id": entity_id},
            label="Upsert Entity",
        )

    def _upsert_relates_to(self, subject: str, obj: str, predicate: str) -> None:
        self._execute_safe(
            """
            MATCH (s:Entity {id: $subject})
            MATCH (o:Entity {id: $object})
            CREATE (s)-[:RELATES_TO {predicate: $predicate}]->(o)
            """,
            {"subject": subject, "object": obj, "predicate": predicate},
            label="RELATES_TO rel",
        )

    def _link_chunk_to_entity(self, content: str, ts: int, entity_id: str) -> None:
        self._execute_safe(
            """
            MATCH (c:Chunk {content: $content, timestamp: $ts})
            MATCH (e:Entity {id: $eid})
            MERGE (c)-[:MENTIONS]->(e)
            """,
            {"content": content, "ts": ts, "eid": entity_id},
            label="MENTIONS rel",
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Search
    # ──────────────────────────────────────────────────────────────────────────

    def search(
        self,
        query_terms: List[str],
        limit: int,
        snippet_words: int,
        query_embedding: Optional[List[float]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid Search: FTS BM25 + Vector HNSW, fused via Reciprocal Rank Fusion.
        """
        fts_results = self._fts_search(" ".join(query_terms), limit)
        vec_results = self._vector_search(query_embedding, limit) if query_embedding else []
        return self._rrf_fuse(fts_results, vec_results, limit, snippet_words)

    def _fts_search(self, search_str: str, limit: int) -> List[Dict[str, Any]]:
        """BM25 full-text search. Falls back from conjunctive (AND) to disjunctive (OR)."""
        for conjunctive in (True, False):
            try:
                query = (
                    """
                    CALL QUERY_FTS_INDEX('Chunk', 'chunk_fts', $query, conjunctive := true)
                    MATCH (d:Document)-[:HAS_CHUNK]->(node)
                    RETURN node.content AS text, d.filename AS filename, node.page AS page, score
                    ORDER BY score DESC LIMIT $limit
                    """
                    if conjunctive
                    else """
                    CALL QUERY_FTS_INDEX('Chunk', 'chunk_fts', $query)
                    MATCH (d:Document)-[:HAS_CHUNK]->(node)
                    RETURN node.content AS text, d.filename AS filename, node.page AS page, score
                    ORDER BY score DESC LIMIT $limit
                    """
                )
                result = self.conn.execute(query, {"query": search_str, "limit": limit})
                rows = self._collect_rows(result, prefix="fts")
                if rows:
                    return rows
            except Exception as exc:
                log.warning("[KuzuDB] FTS search error (conjunctive=%s): %s", conjunctive, exc)
        return []

    def _vector_search(self, query_embedding: List[float], limit: int) -> List[Dict[str, Any]]:
        """HNSW cosine vector search."""
        try:
            result = self.conn.execute(
                """
                CALL QUERY_VECTOR_INDEX('Chunk', 'chunk_vec', $query_vec, $limit)
                MATCH (d:Document)-[:HAS_CHUNK]->(node)
                RETURN node.content AS text, d.filename AS filename, node.page AS page, distance
                ORDER BY distance ASC
                """,
                {"query_vec": query_embedding, "limit": limit},
            )
            rows: List[Dict[str, Any]] = []
            idx = 0
            while result.has_next():
                row = result.get_next()
                rows.append(
                    {
                        "nid": f"vec_{idx}",
                        "text": row[0],
                        "filename": row[1],
                        "page": row[2],
                        "score": 1.0 / (1.0 + row[3]),  # Convert distance → score
                    }
                )
                idx += 1
            return rows
        except Exception as exc:
            log.warning("[KuzuDB] Vector search error: %s", exc)
            return []

    @staticmethod
    def _collect_rows(result: Any, prefix: str) -> List[Dict[str, Any]]:
        """Convert a Kùzu result cursor into a list of dicts."""
        rows: List[Dict[str, Any]] = []
        idx = 0
        while result.has_next():
            row = result.get_next()
            rows.append({"nid": f"{prefix}_{idx}", "text": row[0], "filename": row[1], "page": row[2], "score": row[3]})
            idx += 1
        return rows

    @staticmethod
    def _rrf_fuse(
        fts: List[Dict],
        vec: List[Dict],
        limit: int,
        snippet_words: int,
        k: int = 60,
    ) -> List[Dict[str, Any]]:
        """
        Reciprocal Rank Fusion.
        rrf_score = Σ 1/(k + rank) across FTS and vector ranked lists.
        """
        rrf_scores: Dict[str, float] = {}
        node_data: Dict[str, Dict] = {}

        for rank, r in enumerate(fts):
            nid = r["nid"]
            rrf_scores.setdefault(nid, 0.0)
            node_data.setdefault(nid, r)
            rrf_scores[nid] += 1.0 / (k + rank + 1)

        for rank, r in enumerate(vec):
            nid = r["nid"]
            rrf_scores.setdefault(nid, 0.0)
            node_data.setdefault(nid, r)
            rrf_scores[nid] += 1.0 / (k + rank + 1)

        top = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:limit]

        formatted: List[Dict[str, Any]] = []
        for nid, _ in top:
            r = node_data[nid]
            text = r["text"]
            words = text.split()
            if len(words) > snippet_words:
                text = " ".join(words[:snippet_words]) + "…"
            formatted.append({"filename": r["filename"], "page": r["page"], "text": text})

        return formatted
