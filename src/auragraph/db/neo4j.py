from typing import Any, Dict, List

from neo4j import GraphDatabase

from auragraph.db.base import BaseGraphDB


class Neo4jDB(BaseGraphDB):
    """
    Experimental Graph Database using Neo4j.
    Supports Cypher traversals, Full-Text indexing, and preparing for Graph Laplacian scoring.
    """

    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.init_schema()

    def close(self):
        self.driver.close()

    def init_schema(self) -> None:
        """
        Creates constraints to enforce uniqueness for deduplication, and
        a Full-Text Search index on chunk contents for Phase 2 Keyword matching.
        """
        queries = [
            "CREATE CONSTRAINT document_uq IF NOT EXISTS FOR (d:Document) REQUIRE d.filename IS UNIQUE",
            "CREATE CONSTRAINT entity_uq IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
            "CREATE FULLTEXT INDEX chunk_content IF NOT EXISTS FOR (c:Chunk) ON EACH [c.content]",
            "CREATE VECTOR INDEX chunk_embedding IF NOT EXISTS FOR (c:Chunk) ON (c.embedding) OPTIONS {indexConfig: {`vector.dimensions`: 384, `vector.similarity_function`: 'cosine'}}",
        ]
        with self.driver.session() as session:
            for q in queries:
                try:
                    session.run(q)
                except Exception as e:
                    print(f"[!] Neo4j Schema Init Warning: {e}")

    def is_ingested(self, filename: str) -> bool:
        query = "MATCH (d:Document {filename: $filename}) RETURN d"
        with self.driver.session() as session:
            result = session.run(query, filename=filename)
            return result.single() is not None

    def insert_document(
        self,
        filename: str,
        content: str,
        metadata: Dict[str, Any],
        embedding: List[float] = None,
        triples: List[Dict[str, str]] = None,
    ) -> None:
        """
        Inserts a document structure, optional vectors, and entity triples.
        """
        # Assuming apoc is not installed, fallback to simple set:
        chunk_query = """
        MERGE (d:Document {filename: $filename})
        ON CREATE SET d.ingested_at = timestamp()

        CREATE (c:Chunk {
            content: $content,
            page: $page,
            timestamp: timestamp()
        })
        CREATE (d)-[:HAS_CHUNK]->(c)
        WITH c WHERE $embedding IS NOT NULL
        SET c.embedding = $embedding
        """

        page = metadata.get("page", 1)
        with self.driver.session() as session:
            try:
                session.run(
                    chunk_query,
                    filename=filename,
                    content=content,
                    page=page,
                    embedding=embedding,
                )
            except Exception as e:
                print(f"[!] Error inserting chunk: {e}")

        # 2. Extract Triples (Synapse)
        if triples:
            triple_query = """
            MATCH (d:Document {filename: $filename})-[:HAS_CHUNK]->(c:Chunk {content: $content})
            UNWIND $triples AS t
            MERGE (sub:Entity {id: t.subject})
            MERGE (obj:Entity {id: t.object})
            MERGE (sub)-[rel:RELATES_TO {predicate: t.predicate}]->(obj)
            MERGE (c)-[:MENTIONS]->(sub)
            MERGE (c)-[:MENTIONS]->(obj)
            """
            try:
                with self.driver.session() as session:
                    session.run(
                        triple_query,
                        filename=filename,
                        content=content,
                        triples=triples,
                    )
            except Exception as e:
                print(f"[!] Error inserting triples: {e}")

    def search(
        self,
        query_terms: List[str],
        limit: int,
        snippet_words: int,
        query_embedding: List[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Executes a Hybrid Search. FTS5 exact keyword + Vector Embeddings via RRF.
        """
        match_query = " AND ".join(query_terms)

        # 1. Full-Text Search
        fts_query = """
        CALL db.index.fulltext.queryNodes("chunk_content", $match_query) YIELD node, score
        MATCH (d:Document)-[:HAS_CHUNK]->(node)
        RETURN elementId(node) AS id, d.filename AS filename, node.page AS page, node.content AS text, score
        ORDER BY score DESC
        LIMIT toInteger($limit)
        """

        # 2. Vector Search
        vec_query = """
        CALL db.index.vector.queryNodes("chunk_embedding", $limit, $query_embedding) YIELD node, score
        MATCH (d:Document)-[:HAS_CHUNK]->(node)
        RETURN elementId(node) AS id, d.filename AS filename, node.page AS page, node.content AS text, score
        ORDER BY score DESC
        """

        fts_results = []
        vec_results = []

        with self.driver.session() as session:
            try:
                # FTS Run
                r_fts = session.run(fts_query, match_query=match_query, limit=limit)
                fts_results = [dict(r) for r in r_fts]
                if not fts_results:
                    # Fallback to OR
                    r_fts = session.run(fts_query, match_query=" OR ".join(query_terms), limit=limit)
                    fts_results = [dict(r) for r in r_fts]

                # Vector Run
                if query_embedding:
                    r_vec = session.run(vec_query, query_embedding=query_embedding, limit=limit)
                    vec_results = [dict(r) for r in r_vec]
            except Exception as e:
                print(f"[!] Neo4j Hybrid Search Error: {e}")

        # 3. Reciprocal Rank Fusion (RRF)
        # RRF Score = 1 / (k + rank)
        k = 60
        rrf_scores = {}
        node_data = {}

        for rank, r in enumerate(fts_results):
            cid = r["id"]
            if cid not in rrf_scores:
                rrf_scores[cid] = 0
                node_data[cid] = r
            rrf_scores[cid] += 1.0 / (k + rank + 1)

        for rank, r in enumerate(vec_results):
            cid = r["id"]
            if cid not in rrf_scores:
                rrf_scores[cid] = 0
                node_data[cid] = r
            rrf_scores[cid] += 1.0 / (k + rank + 1)

        # Sort and take top matches
        sorted_nodes = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:limit]

        formatted_results = []
        for cid, score in sorted_nodes:
            r = node_data[cid]
            text = r["text"]
            words = text.split()
            if len(words) > snippet_words:
                text = " ".join(words[:snippet_words]) + "..."

            formatted_results.append(
                {
                    "filename": r["filename"],
                    "page": r["page"],
                    "text": text,
                    "score": score,
                }
            )

        return formatted_results
