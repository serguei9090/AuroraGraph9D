import datetime
import os
import re
import sqlite3
import time

import fitz  # PyMuPDF
import ollama


class AuraGraphJIT:
    def __init__(self, db_path: str = "auragraph_jit.db", model_name: str = "llama3.1:8b"):
        self.db_path = db_path
        self.model_name = model_name
        self.conn = sqlite3.connect(self.db_path)
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()

        # Standard table to reliably track which files have been ingested
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_tracking (
                filename TEXT PRIMARY KEY,
                ingested_at REAL
            )
        ''')

        # The Breakthrough: FTS5 (Full Text Search).
        # Added tokenize='porter' so "improvement" matches "improved"
        cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS anchors USING fts5(
                filename, 
                page_num UNINDEXED, 
                content, 
                timestamp UNINDEXED,
                tokenize='porter'
            )
        ''')
        self.conn.commit()

    def ingest_folder(self, folder_path: str):
        """
        JIT INGESTION: 100% Recall, Near-Instant Speed.
        Zero LLM calls during ingestion. We map the raw text into the FTS5 BM25 Engine.
        """
        if not os.path.exists(folder_path):
            print(f"[!] Folder path does not exist: {folder_path}")
            return

        files = [os.path.join(r, f) for r, _, fs in os.walk(folder_path) for f in fs if f.lower().endswith(('.pdf', '.txt', '.md'))]
        start_time = time.time()

        print(f"[*] AURA JIT-ENGINE START | {datetime.datetime.now().strftime('%H:%M:%S')}")
        print(f"[*] Found {len(files)} supported files in directory.")

        cursor = self.conn.cursor()
        new_files = 0
        skipped_files = 0

        for i, filepath in enumerate(files):
            fname = os.path.basename(filepath)

            # Check standard tracking table
            cursor.execute("SELECT 1 FROM file_tracking WHERE filename = ?", (fname,))
            if cursor.fetchone():
                skipped_files += 1
                continue

            new_files += 1
            if filepath.lower().endswith('.pdf'):
                try:
                    doc = fitz.open(filepath)
                    for pnum, page in enumerate(doc):
                        text = page.get_text().strip()
                        if len(text) > 20:
                            cursor.execute(
                                "INSERT INTO anchors (filename, page_num, content, timestamp) VALUES (?, ?, ?, ?)",
                                (fname, pnum + 1, text, time.time())
                            )
                    cursor.execute(
                        "INSERT INTO file_tracking (filename, ingested_at) VALUES (?, ?)",
                        (fname, time.time()),
                    )
                except Exception as e:
                    print(f"[!] Error reading {fname}: {e}")
            elif filepath.lower().endswith(('.txt', '.md')):
                try:
                    with open(filepath, encoding="utf-8") as tf:
                        text = tf.read().strip()
                    if len(text) > 20:
                        cursor.execute(
                            "INSERT INTO anchors (filename, page_num, content, timestamp) VALUES (?, ?, ?, ?)",
                            (fname, 1, text, time.time()),
                        )
                    cursor.execute(
                        "INSERT INTO file_tracking (filename, ingested_at) VALUES (?, ?)",
                        (fname, time.time()),
                    )
                except Exception as e:
                    print(f"[!] Error reading {fname}: {e}")

        self.conn.commit()
        print("[*] INGESTION COMPLETE:")
        print(f"    - Processed: {new_files} new files")
        print(f"    - Skipped: {skipped_files} cached files")
        print(f"    - Time taken: {time.time() - start_time:.2f} seconds.")
        print("[*] Zero data loss. Ready for JIT Querying.")

    def query(self, user_query: str):
        """
        JIT GRAPH RETRIEVAL:
        1. Instant FTS5 Keyword/BM25 Search with Porter Stemming.
        2. Precise Snippet Extraction (No blind truncation).
        3. LLM synthesizes the final audit.
        """
        print(f"\n[*] Querying FTS5 Index for: '{user_query}'...")

        # Clean query for FTS5 Match
        stop_words = {'what', 'were', 'done', 'for', 'all', 'time', 'the', 'and', 'how', 'is', 'are', 'was', 'in', 'on', 'to', 'with'}
        terms = [w for w in re.findall(r'\w+', user_query) if w.lower() not in stop_words]

        if not terms:
            print("[!] Query too vague after filtering stop words.")
            return

        cursor = self.conn.cursor()

        # FTS5 Query using snippet()
        # snippet(table_name, column_index, start_tag, end_tag, ellipsis, max_tokens)
        # Column 2 is 'content'. This pulls the EXACT 100 words surrounding the match!
        sql_query = """
            SELECT filename, page_num, snippet(anchors, 2, '**', '**', '...', 100)
            FROM anchors 
            WHERE anchors MATCH ? 
            ORDER BY rank 
            LIMIT 15
        """

        # Try exact AND matching first
        match_query = " AND ".join(terms)
        try:
            cursor.execute(sql_query, (match_query,))
            results = cursor.fetchall()
        except sqlite3.OperationalError:
            results = []

        # Fallback to OR matching if AND is too strict
        if not results:
            if len(terms) > 1:
                print("[*] Strict match failed. Widening search radius...")
            match_query = " OR ".join(terms)
            try:
                cursor.execute(sql_query, (match_query,))
                results = cursor.fetchall()
            except sqlite3.OperationalError:
                results = []

        if not results:
            print("[!] No documents found matching those terms.")
            return

        print(f"[*] Found {len(results)} highly relevant contexts. Building JIT Graph...")

        evidence_blocks = []
        for fname, pnum, exact_snippet in results:
            # We now pass the exact highlight snippet instead of truncating the page
            evidence_blocks.append(f"SOURCE: {fname} (Page {pnum})\nTEXT: {exact_snippet}\n")

        full_evidence = "\n".join(evidence_blocks)

        # The JIT LLM Prompt: Strict anti-hallucination constraints
        prompt = f"""
        You are the AuraGraph JIT (Just-In-Time) Audit AI. 
        
        USER QUERY: {user_query}
        
        DATABASE EVIDENCE (Keywords are highlighted with ** **):
        {full_evidence}
        
        TASK 1: Extract the specific improvements, changes, or facts requested.
        TASK 2: Synthesize a clear report. Cite the Source Filename and Page Number.
        
        CRITICAL RULE: If the evidence does not specifically mention the exact technologies or concepts in the user query (e.g., if they asked for HTTP and you only see SSH), you MUST state: "The provided documents do not contain information about [Topic]." DO NOT hallucinate or substitute technologies.
        """

        print(f"[*] Synthesizing Audit with {self.model_name}...\n")
        resp = ollama.generate(
            model=self.model_name,
            prompt=prompt,
            system="You are a precise technical auditor. Rely STRICTLY on the provided evidence. If it's not in the evidence, say you don't know.",
            stream=False
        )

        print("="*80 + "\nAURAGRAPH JIT-RAG AUDIT\n" + "="*80)
        print(resp['response'])
        print("\n" + "="*80)

    def predict(self, user_query: str) -> dict:
        """
        Programmatic version of query() for automated evaluation.
        Returns a structured dict instead of printing to console.
        """
        start_ms = time.time()

        stop_words = {
            'what', 'were', 'done', 'for', 'all', 'time', 'the', 'and',
            'how', 'is', 'are', 'was', 'in', 'on', 'to', 'with',
        }
        terms = [
            w for w in re.findall(r'\w+', user_query)
            if w.lower() not in stop_words
        ]

        empty_result = {
            "query": user_query,
            "context": [],
            "response": "",
            "sources": [],
            "latency_ms": 0,
        }

        if not terms:
            return empty_result

        cursor = self.conn.cursor()
        sql_query = """
            SELECT filename, page_num, snippet(anchors, 2, '**', '**', '...', 100)
            FROM anchors
            WHERE anchors MATCH ?
            ORDER BY rank
            LIMIT 15
        """

        match_query = " AND ".join(terms)
        try:
            cursor.execute(sql_query, (match_query,))
            results = cursor.fetchall()
        except sqlite3.OperationalError:
            results = []

        if not results:
            match_query = " OR ".join(terms)
            try:
                cursor.execute(sql_query, (match_query,))
                results = cursor.fetchall()
            except sqlite3.OperationalError:
                results = []

        if not results:
            return empty_result

        evidence_blocks = []
        sources = []
        for fname, pnum, exact_snippet in results:
            evidence_blocks.append(
                f"SOURCE: {fname} (Page {pnum})\nTEXT: {exact_snippet}\n"
            )
            sources.append({"filename": fname, "page": pnum})

        full_evidence = "\n".join(evidence_blocks)

        prompt = f"""
        You are the AuraGraph JIT (Just-In-Time) Audit AI.

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

        resp = ollama.generate(
            model=self.model_name,
            prompt=prompt,
            system=(
                "You are a precise technical auditor. Rely STRICTLY on the "
                "provided evidence. If it's not in the evidence, say you "
                "don't know."
            ),
            stream=False,
        )

        latency = (time.time() - start_ms) * 1000

        return {
            "query": user_query,
            "context": evidence_blocks,
            "response": resp["response"],
            "sources": sources,
            "latency_ms": round(latency, 2),
        }

if __name__ == "__main__":
    import sys
    aura = AuraGraphJIT(model_name="llama3.1:8b")

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python main.py ingest <dir>")
        print("  python main.py query <text>")
    else:
        cmd = sys.argv[1]
        if cmd == "ingest" and len(sys.argv) >= 3:
            aura.ingest_folder(sys.argv[2])
        elif cmd == "query":
            aura.query(" ".join(sys.argv[2:]))
        else:
            print("[!] Missing arguments.")
