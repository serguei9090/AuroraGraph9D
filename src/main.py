import os
import re
import json
import uuid
import sqlite3
import datetime
import numpy as np
import networkx as nx
from typing import List, Dict, Any, Tuple
from collections import Counter
import fitz  # PyMuPDF
import ollama # Use the official library

class AuraGraph9D:
    def __init__(self, db_path: str = "auragraph_9d.db", model_name: str = "llama3.1:8b", debug: bool = True):
        self.db_path = db_path
        # Using ONE model for both to prevent VRAM swapping
        self.model_name = model_name
        self.debug = debug
        self.conn = sqlite3.connect(self.db_path)
        self._init_db()
        
    def _init_db(self):
        cursor = self.conn.cursor()
        # Dimensions 1-9: Logic (1-3), Context (4), Authority (5), Time (6), Pointer (7), Scope/Page (8), Semantic Alias (9)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS synapses (
                id TEXT PRIMARY KEY, subject TEXT, relation TEXT, object TEXT, 
                context TEXT, source_id TEXT, timestamp REAL, 
                blob_pointer INTEGER, page_num INTEGER, scope TEXT, semantic_hash TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS anchors (
                source_id TEXT PRIMARY KEY, filename TEXT, 
                full_content TEXT, timestamp REAL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS aliases (
                term TEXT PRIMARY KEY, canonical TEXT
            )
        ''')
        self.conn.commit()

    def ingest_folder(self, folder_path: str):
        if not os.path.exists(folder_path):
            print(f"[!] Folder not found: {folder_path}")
            return

        supported_extensions = ('.pdf', '.md', '.txt', '.log')
        files_to_process = []
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(supported_extensions):
                    files_to_process.append(os.path.join(root, file))

        print(f"[*] Found {len(files_to_process)} files. Using Unified {self.model_name}...")
        for i, filepath in enumerate(files_to_process):
            self.ingest_hyper_speed(filepath)

    def ingest_hyper_speed(self, filepath: str):
        filename = os.path.basename(filepath)
        cursor = self.conn.cursor()
        cursor.execute("SELECT source_id FROM anchors WHERE filename = ?", (filename,))
        if cursor.fetchone():
            if self.debug: print(f"[*] {filename} cached. Skipping.")
            return

        print(f"\n[*] Hyper-Speed Ingestion: {filename}")
        source_id = str(uuid.uuid4())
        full_text = ""
        
        try:
            pages_to_process = []
            if filepath.endswith('.pdf'):
                doc = fitz.open(filepath)
                doc_text = "\n".join([p.get_text() for p in doc])
                word_freq = Counter(re.findall(r'\b\w{4,}\b', doc_text.lower()))
                
                for page_num, page in enumerate(doc):
                    page_text = page.get_text()
                    if not page_text.strip(): continue
                    full_text += page_text + "\n"
                    
                    page_words = re.findall(r'\b\w{4,}\b', page_text.lower())
                    importance = sum(1/word_freq[w] for w in page_words if w in word_freq)
                    
                    if importance >= 1.2:
                        pages_to_process.append((page_text, page_num + 1))
            
            # BATCH PROCESSING (5 pages per call)
            batch_size = 5
            for i in range(0, len(pages_to_process), batch_size):
                batch = pages_to_process[i:i + batch_size]
                self._map_batch_logic(batch, source_id, filename)

            cursor.execute("INSERT INTO anchors VALUES (?, ?, ?, ?)", 
                           (source_id, filename, full_text, datetime.datetime.now().timestamp()))
            self.conn.commit()
            print(f"[*] Integrated {filename}.")
        except Exception as e:
            print(f"[!] Error in {filename}: {e}")

    def _map_batch_logic(self, batch: List[Tuple[str, int]], source_id: str, filename: str):
        combined_text = ""
        for text, pnum in batch:
            combined_text += f"--- PAGE {pnum} ---\n{text[:2000]}\n"
        
        if self.debug: 
            p_range = f"{batch[0][1]}-{batch[-1][1]}" if len(batch) > 1 else f"{batch[0][1]}"
            print(f"    > Mapping Page Batch {p_range}...")

        prompt = f"""
        Analyze this technical content. Extract logical synapses (subject, relation, obj, context).
        Return ONLY a JSON list under the key 'synapses'.
        CONTENT:
        {combined_text}
        """
        
        try:
            response = ollama.generate(
                model=self.model_name,
                prompt=prompt,
                system="Strict JSON extractor. Context is technical documentation.",
                format="json",
                options={"temperature": 0.0},
                stream=False
            )
            
            # Scrub markdown blocks if they exist
            resp_text = response['response'].strip()
            if resp_text.startswith("```"):
                resp_text = re.sub(r'^```[a-z]*\n', '', resp_text)
                resp_text = re.sub(r'\n```$', '', resp_text)

            data = json.loads(resp_text)
            
            cursor = self.conn.cursor()
            syn_list = data.get('synapses', []) if isinstance(data.get('synapses'), list) else []
            
            for syn in syn_list:
                sub = str(syn.get('subject', '')).lower().strip()
                if not sub or len(sub) < 2: continue
                
                rel = str(syn.get('relation', 'is'))
                obj = str(syn.get('obj', 'unknown')).lower().strip()
                ctx = syn.get('context', 'technical')
                if isinstance(ctx, list): ctx = ", ".join(map(str, ctx))
                else: ctx = str(ctx)
                
                cursor.execute("INSERT INTO synapses VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                               (str(uuid.uuid4()), sub, rel, obj, ctx, 
                                source_id, datetime.datetime.now().timestamp(), 
                                combined_text.find(sub[:10]), batch[0][1], filename, str(hash(sub))))
            self.conn.commit()
        except Exception as e:
            if self.debug: print(f"    [!] Batch Mapping Error: {e}")

    def query(self, user_query: str):
        stop_words = {'what', 'were', 'done', 'for', 'all', 'time', 'the', 'and', 'how', 'is', 'are', 'was'}
        raw_words = [w.lower() for w in re.findall(r'\w+', user_query) if len(w) > 2 and w.lower() not in stop_words]
        
        cursor = self.conn.cursor()
        expanded = set(raw_words)
        for w in raw_words:
            cursor.execute("SELECT canonical FROM aliases WHERE term = ?", (w,))
            res = cursor.fetchone()
            if res: expanded.add(res[0])
        
        results = []
        for w in expanded:
            cursor.execute("SELECT * FROM synapses WHERE subject LIKE ? OR object LIKE ? OR scope LIKE ?", (f"%{w}%", f"%{w}%", f"%{w}%"))
            results.extend(cursor.fetchall())

        if not results:
            print("[!] No neural paths found. Try simpler terms.")
            return

        results = sorted(results, key=lambda x: x[6], reverse=True)
        evidence, seen = [], set()
        
        for f in results:
            key = f"{f[1]}-{f[3]}"
            if key in seen: continue
            seen.add(key)
            
            cursor.execute("SELECT full_content, filename FROM anchors WHERE source_id = ?", (f[5],))
            res = cursor.fetchone()
            
            if res is None:
                continue
                
            blob = res[0]
            fname = res[1]
            
            start = max(0, f[7] - 1500)
            end = min(len(blob), f[7] + 3500)
            evidence.append({"logic": f"[{f[1]}]--{f[2]}-->[{f[3]}]", "src": fname, "page": f[8], "text": blob[start:end]})
            if len(evidence) >= 5: break

        if not evidence:
            print("[!] Found logic connections but the source documents are missing.")
            return

        ctx = "\n".join([f"DOC: {e['src']} (P.{e['page']})\nLOGIC: {e['logic']}\nCONTENT:\n{e['text']}\n" for e in evidence])
        resp = ollama.generate(
            model=self.model_name,
            prompt=f"User Query: {user_query}\n\nEvidence:\n{ctx}\n\nExplain technical audit based on evidence.",
            stream=False
        )
        print("\n" + "="*80 + "\nAURAGRAPH 9D AUDIT\n" + "="*80)
        print(resp['response'])
        print("="*80 + "\n")

    def visualize(self):
        from dash import Dash, html, dcc
        import plotly.graph_objects as go
        app = Dash(__name__)
        cursor = self.conn.cursor()
        cursor.execute("SELECT subject, object FROM synapses LIMIT 1000")
        rows = cursor.fetchall()
        G = nx.Graph()
        for s, o in rows: G.add_edge(s, o)
        pos = nx.spring_layout(G)
        edge_x, edge_y = [], []
        for e in G.edges():
            x0, y0 = pos[e[0]]; x1, y1 = pos[e[1]]
            edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
        node_x, node_y, node_text = [], [], []
        for n in G.nodes():
            x, y = pos[n]; node_x.append(x); node_y.append(y); node_text.append(n)
        fig = go.Figure(data=[
            go.Scatter(x=edge_x, y=edge_y, line=dict(width=0.5, color='#888'), mode='lines'),
            go.Scatter(x=node_x, y=node_y, mode='markers+text', text=node_text, marker=dict(size=10, color='orange'))
        ])
        app.layout = html.Div([dcc.Graph(figure=fig, style={'height': '95vh'})])
        app.run(debug=False, port=8050)

if __name__ == "__main__":
    import sys
    aura = AuraGraph9D(model_name="llama3.1:8b")
    if len(sys.argv) < 2:
        print("Usage: python main.py [ingest <dir> / query <text> / visualize]")
    else:
        cmd = sys.argv[1]
        if cmd == "visualize": aura.visualize()
        elif len(sys.argv) >= 3:
            val = " ".join(sys.argv[2:])
            if cmd == "ingest": aura.ingest_folder(val)
            elif cmd == "query": aura.query(val)