import sqlite3
import time
from typing import Any, Dict, List

from auragraph.db.base import BaseGraphDB


class SQLiteFTS5DB(BaseGraphDB):
    """
    Experimental 2D local SQLite implementation using FTS5 BM25 search.
    Provides ultra-fast, 0-hallucination semantic keyword matching.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        # Allow multi-threaded access (we manage write safety with locks in the ingestion script)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.init_schema()

    def init_schema(self) -> None:
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_tracking (
                filename TEXT PRIMARY KEY,
                ingested_at REAL
            )
        """)
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS anchors USING fts5(
                filename,
                page_num UNINDEXED,
                content,
                timestamp UNINDEXED,
                tokenize='porter'
            )
        """)
        self.conn.commit()

    def is_ingested(self, filename: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM file_tracking WHERE filename = ?", (filename,))
        return cursor.fetchone() is not None

    def insert_document(
        self,
        filename: str,
        content: str,
        metadata: Dict[str, Any],
        embedding: List[float] = None,
        triples: List[Dict[str, str]] = None,
    ) -> None:
        cursor = self.conn.cursor()
        page_num = metadata.get("page", 1)
        cursor.execute(
            "INSERT INTO anchors (filename, page_num, content, timestamp) VALUES (?, ?, ?, ?)",
            (filename, page_num, content, time.time()),
        )
        # Upsert tracking
        cursor.execute(
            "INSERT OR REPLACE INTO file_tracking (filename, ingested_at) VALUES (?, ?)",
            (filename, time.time()),
        )
        self.conn.commit()

    def search(
        self,
        query_terms: List[str],
        limit: int,
        snippet_words: int,
        query_embedding: List[float] = None,
    ) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        sql_query = f"""
            SELECT filename, page_num, snippet(anchors, 2, '**', '**', '...', {snippet_words})
            FROM anchors
            WHERE anchors MATCH ?
            ORDER BY rank
            LIMIT {limit}
        """

        # Try exact AND matching first
        match_query = " AND ".join(query_terms)
        try:
            cursor.execute(sql_query, (match_query,))
            results = cursor.fetchall()
        except sqlite3.OperationalError:
            results = []

        # Fallback to OR matching
        if not results:
            match_query = " OR ".join(query_terms)
            try:
                cursor.execute(sql_query, (match_query,))
                results = cursor.fetchall()
            except sqlite3.OperationalError:
                results = []

        return [{"filename": row[0], "page": row[1], "text": row[2]} for row in results]
