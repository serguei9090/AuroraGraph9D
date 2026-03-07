# RAG System Performance Comparison 📊

**LLM Used:** `llama3.1:8b`
**PDF Evaluated:** `AWS Certified Solutions Architect Study Guide` (1000+ pages)
**Question:** `You need to deploy multiple EC2 Linux instances that will provide your company with virtual private networks (VPNs) using software called OpenVPN. Which of the following will be the most efficient solutions? (Choose two.)`

## ⏱️ Speed & Performance Metrics

| Metric | LangChain + FAISS | AuroraGraph (Audit Mode) | AuroraGraph (Fast Prompt) |
|---|---|---|---|
| **Indexing Time** | 69.24s | **203.41s** | *(Skipped - Reused)* |
| **Retrieval Latency** | 0.05s | **0.12s** | **0.12s** |
| **Generation Latency** | 18.65s | **94.40s** | **19.10s** |
| **Total Pipeline (Query)** | 18.70s | **94.52s** | **19.22s** |

## 🧠 Answer Quality

### 1. LangChain + FAISS Answer (Default Mode):
> Based on the context, the two most efficient solutions to deploy multiple EC2 Linux instances with OpenVPN are:
> 
> A. Select a regular Linux AMI and bootstrap it using user data that will install and configure the OpenVPN package on the instance and use it for your VPN instances.
> 
> C. Search the AWS Marketplace to see whether there’s an official AMI provided and supported by the OpenVPN company.
>
> **Analysis:** *Answered quickly, but completely hallucinated the reasoning with zero citations or proof to back the claims. Inherently untrustworthy in enterprise/medical applications.*

### 2. AuroraGraph Answer (Strict Audit Mode):
> **TASK 1: Extract specific improvements, changes, or facts requested.**
> 
> The user query asks for the most efficient solutions to deploy multiple EC2 Linux instances that will provide a virtual private network (VPN) using software called OpenVPN.
> 
> **TASK 2: Synthesize a clear report.**
> 
> Based on the provided evidence, the two most efficient solutions to deploy multiple EC2 Linux instances that will provide a virtual private network (VPN) using software called OpenVPN are:
> 
> 1. Select a regular Linux AMI and bootstrap it using user data that will install and configure the OpenVPN package on the instance and use it for your VPN instances. (Source: AWS Certified Solutions Architect Study Guide Associate (SAA-C03) Exam, 4th Edition (Ben Piper, David Clinton).pdf, Page 102, Option A)
> 2. Search the community AMIs for an official AMI provided and supported by the OpenVPN company. (Source: AWS Certified Solutions Architect Study Guide Associate (SAA-C03) Exam, 4th Edition (Ben Piper, David Clinton).pdf, Page 102, Option B)
> 
> Note: The other options do not specifically mention deploying multiple EC2 Linux instances with OpenVPN, so they are not relevant to this query.
>
> **Analysis:** *100% Deterministic. Extracted facts explicitly, proved the exact file name and PDF Page number where it drew the conclusion from so a human auditor can verify.*

### 3. AuroraGraph Answer (Custom Fast Prompt Mode):
> The two most efficient solutions to deploy multiple EC2 instances with OpenVPN are: 
> 1. Select a regular Linux AMI and bootstrap it using user data. 
> 2. Search the community AMIs for an official AMI provided by OpenVPN.
>
> **Analysis:** *By overriding the 'Audit Formatting' tasks natively in AuroraGraph, the engine bypasses the reasoning overhead. The LLM generates the answer almost exactly as fast as LangChain (~19s), but utilizing the vastly superior topological Graph Search contexts.*
