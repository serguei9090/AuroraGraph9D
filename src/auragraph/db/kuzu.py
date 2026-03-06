from typing import Any, Dict, List

import kuzu

from auragraph.db.base import BaseGraphDB


class KuzuDB(BaseGraphDB):
    """
    Embedded 10D Graph Database using Kùzu.
    Zero-setup, no Docker required. Uses Cypher queries with native
    FTS (BM25) and Vector (HNSW) indexes for Hybrid Search.
    """

    def __init__(self, db_path: str = "./auragraph_graph"):
        self.db_path = db_path
        self.db = kuzu.Database(db_path)
        self.conn = kuzu.Connection(self.db)
        self.init_schema()

    def init_schema(self) -> None:
        """
        Creates node/relationship tables and installs FTS + Vector extensions.
        Uses IF NOT EXISTS to be idempotent.
        """
        # Install extensions
        try:
            self.conn.execute("INSTALL fts; LOAD fts;")
        except Exception:
            pass  # Already installed
        try:
            self.conn.execute("INSTALL vector; LOAD vector;")
        except Exception:
            pass  # Already installed

        schema_queries = [
            # Node Tables
            "CREATE NODE TABLE IF NOT EXISTS Document(filename STRING PRIMARY KEY, ingested_at INT64)",
            "CREATE NODE TABLE IF NOT EXISTS Chunk(id SERIAL PRIMARY KEY, content STRING, page INT64, embedding FLOAT[384], timestamp INT64)",
            "CREATE NODE TABLE IF NOT EXISTS Entity(id STRING PRIMARY KEY)",
            # Relationship Tables
            "CREATE REL TABLE IF NOT EXISTS HAS_CHUNK(FROM Document TO Chunk)",
            "CREATE REL TABLE IF NOT EXISTS MENTIONS(FROM Chunk TO Entity)",
            "CREATE REL TABLE IF NOT EXISTS RELATES_TO(FROM Entity TO Entity, predicate STRING)",
        ]
        for q in schema_queries:
            try:
                self.conn.execute(q)
            except Exception as e:
                # Table already exists or similar non-critical error
                if "already exists" not in str(e).lower():
                    print(f"[!] Kùzu Schema Warning: {e}")

        # Create FTS Index on Chunk content
        try:
            self.conn.execute("CALL CREATE_FTS_INDEX('Chunk', 'chunk_fts', ['content'], stemmer := 'porter')")
        except Exception:
            pass  # Index already exists

        # Create Vector Index on Chunk embeddings
        try:
            self.conn.execute("CALL CREATE_VECTOR_INDEX('Chunk', 'chunk_vec', 'embedding')")
        except Exception:
            pass  # Index already exists

    def is_ingested(self, filename: str) -> bool:
        result = self.conn.execute(
            "MATCH (d:Document {filename: $filename}) RETURN d.filename",
            {"filename": filename},
        )
        return result.has_next()

    def insert_document(
        self,
        filename: str,
        content: str,
        metadata: Dict[str, Any],
        embedding: List[float] = None,
        triples: List[Dict[str, str]] = None,
    ) -> None:
        """
        Inserts a Document->Chunk structure with optional embedding and triples.
        """
        import time as _time

        page = metadata.get("page", 1)
        ts = int(_time.time())

        # 1. Merge Document node
        self.conn.execute(
            "MERGE (d:Document {filename: $filename}) ON CREATE SET d.ingested_at = $ts",
            {"filename": filename, "ts": ts},
        )

        # 2. Create Chunk node
        if embedding:
            self.conn.execute(
                "CREATE (c:Chunk {content: $content, page: $page, embedding: $embedding, timestamp: $ts})",
                {"content": content, "page": page, "embedding": embedding, "ts": ts},
            )
        else:
            self.conn.execute(
                "CREATE (c:Chunk {content: $content, page: $page, timestamp: $ts})",
                {"content": content, "page": page, "ts": ts},
            )

        # 3. Create HAS_CHUNK relationship
        self.conn.execute(
            """
            MATCH (d:Document {filename: $filename})
            MATCH (c:Chunk {content: $content, timestamp: $ts})
            CREATE (d)-[:HAS_CHUNK]->(c)
            """,
            {"filename": filename, "content": content, "ts": ts},
        )

        # 4. Insert Triples (10D Synapse)
        if triples:
            for t in triples:
                try:
                    self.conn.execute(
                        "MERGE (s:Entity {id: $subject})",
                        {"subject": t["subject"]},
                    )
                    self.conn.execute(
                        "MERGE (o:Entity {id: $object})",
                        {"object": t["object"]},
                    )
                    self.conn.execute(
                        """
                        MATCH (s:Entity {id: $subject})
                        MATCH (o:Entity {id: $object})
                        CREATE (s)-[:RELATES_TO {predicate: $predicate}]->(o)
                        """,
                        {
                            "subject": t["subject"],
                            "object": t["object"],
                            "predicate": t["predicate"],
                        },
                    )
                    # Link chunk to entities
                    self.conn.execute(
                        """
                        MATCH (c:Chunk {content: $content, timestamp: $ts})
                        MATCH (e:Entity {id: $eid})
                        CREATE (c)-[:MENTIONS]->(e)
                        """,
                        {"content": content, "ts": ts, "eid": t["subject"]},
                    )
                    self.conn.execute(
                        """
                        MATCH (c:Chunk {content: $content, timestamp: $ts})
                        MATCH (e:Entity {id: $eid})
                        CREATE (c)-[:MENTIONS]->(e)
                        """,
                        {"content": content, "ts": ts, "eid": t["object"]},
                    )
                except Exception as e:
                    print(f"[!] Kùzu Triple Insert Warning: {e}")

    def search(
        self,
        query_terms: List[str],
        limit: int,
        snippet_words: int,
        query_embedding: List[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid Search: FTS BM25 + Vector HNSW, fused via Reciprocal Rank Fusion.
        """
        fts_results = []
        vec_results = []

        # 1. Full-Text Search (BM25)
        search_str = " ".join(query_terms)
        try:
            # Conjunctive first (AND)
            result = self.conn.execute(
                """
                CALL QUERY_FTS_INDEX('Chunk', 'chunk_fts', $query, conjunctive := true)
                MATCH (d:Document)-[:HAS_CHUNK]->(node)
                RETURN node.content AS text, d.filename AS filename, node.page AS page, score
                ORDER BY score DESC
                LIMIT $limit
                """,
                {"query": search_str, "limit": limit},
            )
            idx = 0
            while result.has_next():
                row = result.get_next()
                fts_results.append(
                    {
                        "nid": f"fts_{idx}",
                        "text": row[0],
                        "filename": row[1],
                        "page": row[2],
                        "score": row[3],
                    }
                )
                idx += 1

            # Fallback to disjunctive (OR) if no conjunctive results
            if not fts_results:
                result = self.conn.execute(
                    """
                    CALL QUERY_FTS_INDEX('Chunk', 'chunk_fts', $query)
                    MATCH (d:Document)-[:HAS_CHUNK]->(node)
                    RETURN node.content AS text, d.filename AS filename, node.page AS page, score
                    ORDER BY score DESC
                    LIMIT $limit
                    """,
                    {"query": search_str, "limit": limit},
                )
                idx = 0
                while result.has_next():
                    row = result.get_next()
                    fts_results.append(
                        {
                            "nid": f"fts_{idx}",
                            "text": row[0],
                            "filename": row[1],
                            "page": row[2],
                            "score": row[3],
                        }
                    )
                    idx += 1
        except Exception as e:
            print(f"[!] Kùzu FTS Search Error: {e}")

        # 2. Vector Search (HNSW Cosine)
        if query_embedding:
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
                idx = 0
                while result.has_next():
                    row = result.get_next()
                    vec_results.append(
                        {
                            "nid": f"vec_{idx}",
                            "text": row[0],
                            "filename": row[1],
                            "page": row[2],
                            "score": 1.0 / (1.0 + row[3]),
                        }
                    )
                    idx += 1
            except Exception as e:
                print(f"[!] Kùzu Vector Search Error: {e}")

        # 3. Reciprocal Rank Fusion (RRF)
        k = 60
        rrf_scores: Dict[Any, float] = {}
        node_data: Dict[Any, Dict] = {}

        for rank, r in enumerate(fts_results):
            nid = r["nid"]
            if nid not in rrf_scores:
                rrf_scores[nid] = 0
                node_data[nid] = r
            rrf_scores[nid] += 1.0 / (k + rank + 1)

        for rank, r in enumerate(vec_results):
            nid = r["nid"]
            if nid not in rrf_scores:
                rrf_scores[nid] = 0
                node_data[nid] = r
            rrf_scores[nid] += 1.0 / (k + rank + 1)

        sorted_nodes = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:limit]

        # Format results with snippet truncation
        formatted = []
        for nid, score in sorted_nodes:
            r = node_data[nid]
            text = r["text"]
            words = text.split()
            if len(words) > snippet_words:
                text = " ".join(words[:snippet_words]) + "..."

            formatted.append({"filename": r["filename"], "page": r["page"], "text": text})

        return formatted
