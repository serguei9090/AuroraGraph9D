import os
import shutil
import sys
import time
from pathlib import Path

import ollama
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Make sure we can import auragraph
auragraph_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(auragraph_dir / "src"))

from auragraph import AuroraGraphEngine  # noqa: E402
from auragraph.db.kuzu import KuzuDB  # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass



# Configuration
DEFAULT_DB_PATH = "./comparison_graph"
TEST_PDF_PATH = os.path.join(auragraph_dir, "code_examples", "knowledge", "AWS Certified Solutions Architect Study Guide  Associate (SAA-C03) Exam, 4th Edition (Ben Piper, David Clinton).pdf")
QUERY = "You need to deploy multiple EC2 Linux instances that will provide your company with virtual private networks (VPNs) using software called OpenVPN. Which of the following will be the most efficient solutions? (Choose two.)"
MODEL_NAME = os.getenv("AURA_MODEL", "llama3.1:8b")

def evaluate_langchain():
    print("\n--- Running Option 1: LangChain + FAISS + SentenceTransformers ---")

    # 1. Ingestion Phase
    start_ingest = time.time()

    print("Loading PDF...")
    loader = PyPDFLoader(TEST_PDF_PATH)
    docs = loader.load()

    print("Splitting Text...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)

    print("Embedding & Indexing (FAISS)...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = FAISS.from_documents(documents=splits, embedding=embeddings)

    ingest_time = time.time() - start_ingest
    print(f"Ingestion took: {ingest_time:.2f} seconds")

    # 2. Retrieval Phase
    start_retrieve = time.time()
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    retrieved_docs = retriever.invoke(QUERY)
    retrieve_time = time.time() - start_retrieve
    print(f"Retrieval took: {retrieve_time:.2f} seconds")

    # 3. LLM Generation
    context = "\n".join([doc.page_content for doc in retrieved_docs])
    prompt = f"Context:\n{context}\n\nQuestion: {QUERY}"

    start_gen = time.time()
    resp = ollama.generate(model=MODEL_NAME, prompt=prompt, system="Answer accurately based on context.", stream=False)
    gen_time = time.time() - start_gen

    return {
        "system": "LangChain + FAISS",
        "ingest_sec": ingest_time,
        "retrieve_sec": retrieve_time,
        "gen_sec": gen_time,
        "total_sec": ingest_time + retrieve_time + gen_time,
        "answer": resp["response"]
    }

def evaluate_auragraph(db_path=DEFAULT_DB_PATH, skip_ingest=False):
    print("\n--- Running Option 2: AuroraGraph (Audit Prompt) ---")

    start_init = time.time()
    engine = AuroraGraphEngine(db=KuzuDB(db_path))
    print(f"Engine Init: {time.time() - start_init:.2f}s")

    ingest_time = 0
    if not skip_ingest:
        # Create isolated folder for the test PDF
        tmp_folder = "./comparison_knowledge"
        os.makedirs(tmp_folder, exist_ok=True)
        shutil.copy(TEST_PDF_PATH, tmp_folder)

        # 1. Ingestion Phase
        start_ingest = time.time()
        print("Ingesting PDF (Extracting, chunking, parsing Graph synapses, FastEmbed embedding)...")
        engine.ingest_folder(tmp_folder)
        ingest_time = time.time() - start_ingest
        print(f"Ingestion took: {ingest_time:.2f} seconds")
        shutil.rmtree(tmp_folder)

    # 2 & 3. Retrieval & Generation (AuroraGraph predict does both)
    # The stats returned separate retrieval vs generation
    print("Querying AuroraGraph (Standard Audit Prompt)...")
    prediction = engine.query(QUERY, stream=False)

    return {
        "system": "AuroraGraph",
        "ingest_sec": ingest_time,
        "retrieve_sec": prediction["retrieval_ms"] / 1000.0,
        "gen_sec": prediction["generation_ms"] / 1000.0,
        "total_sec": ingest_time + (prediction["retrieval_ms"]/1000) + (prediction["generation_ms"]/1000),
        "answer": prediction["response"]
    }

def evaluate_auragraph_simple(db_path=DEFAULT_DB_PATH):
    print("\n--- Running Option 3: AuroraGraph (Simple Fast Prompt) ---")
    engine = AuroraGraphEngine(db=KuzuDB(db_path))

    simple_prompt = "Context:\n{evidence}\n\nQuestion: {query}\n\nAnswer the question concisely based on the context."
    simple_sys_prompt = "You are a helpful assistant."

    print("Querying AuroraGraph (Simple Prompt)...")
    prediction = engine.query(QUERY, stream=False, custom_prompt=simple_prompt, custom_system_prompt=simple_sys_prompt)

    return {
        "system": "AuroraGraph (Fast Prompt)",
        "ingest_sec": 0, # Already ingested by the previous step
        "retrieve_sec": prediction["retrieval_ms"] / 1000.0,
        "gen_sec": prediction["generation_ms"] / 1000.0,
        "total_sec": 0 + (prediction["retrieval_ms"]/1000) + (prediction["generation_ms"]/1000),
        "answer": prediction["response"]
    }

def main():
    if not os.path.exists(TEST_PDF_PATH):
        print(f"Error: Could not find PDF at {TEST_PDF_PATH}")
        sys.exit(1)

    print(f"Starting Comparison Test using LLM: {MODEL_NAME}")

    db_path = DEFAULT_DB_PATH
    # Clean previous DB for fair ingestion test
    if os.path.exists(db_path):
        if os.path.isdir(db_path):
            shutil.rmtree(db_path)
        else:
            os.remove(db_path)

    res1 = evaluate_langchain()
    res2 = evaluate_auragraph(db_path=db_path)
    res3 = evaluate_auragraph_simple(db_path=db_path)

    # Write report
    report_path = os.path.join(auragraph_dir, "comparison", "comparison_result_test.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# RAG System Performance Comparison 📊\n\n")
        f.write("**LLM Used:** `" + MODEL_NAME + "`\n")
        f.write("**PDF Evaluated:** `AWS Certified Solutions Architect Study Guide` (1000+ pages)\n")
        f.write("**Question:** `" + QUERY + "`\n\n")

        f.write("## ⏱️ Speed & Performance Metrics\n\n")
        f.write("| Metric | LangChain + FAISS | AuroraGraph (Audit Mode) | AuroraGraph (Fast Mode) |\n")
        f.write("|---|---|---|---|\n")
        f.write(f"| **Indexing Time** | {res1['ingest_sec']:.2f}s | **{res2['ingest_sec']:.2f}s** | *(Skipped)* |\n")
        f.write(f"| **Retrieval Latency** | {res1['retrieve_sec']:.2f}s | **{res2['retrieve_sec']:.2f}s** | **{res3['retrieve_sec']:.2f}s** |\n")
        f.write(f"| **Generation Latency** | {res1['gen_sec']:.2f}s | **{res2['gen_sec']:.2f}s** | **{res3['gen_sec']:.2f}s** |\n")
        f.write(f"| **Total Pipeline (Query Only)** | {(res1['retrieve_sec'] + res1['gen_sec']):.2f}s | **{(res2['retrieve_sec'] + res2['gen_sec']):.2f}s** | **{(res3['retrieve_sec'] + res3['gen_sec']):.2f}s** |\n\n")

        f.write("## 🧠 Answer Quality\n\n")
        f.write("### 1. LangChain + FAISS Answer:\n")
        f.write(f"> {res1['answer'].strip()}\n\n")

        f.write("### 2. AuroraGraph (Strict Audit Mode) Answer:\n")
        f.write(f"> {res2['answer'].strip()}\n\n")

        f.write("### 3. AuroraGraph (Fast Mode) Answer:\n")
        f.write(f"> {res3['answer'].strip()}\n\n")

    print(f"\nComparison complete! Wrote results to {report_path}")

if __name__ == "__main__":
    main()
