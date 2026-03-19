# SIA-RAG — Semantic Intelligence Architecture for AML Compliance

> **A unified AI platform that answers regulatory questions and automatically audits your internal AML policies for compliance gaps — with zero hallucinations.**

---

## What is SIA-RAG?

SIA-RAG is an intelligent document analysis system built specifically for **Anti-Money Laundering (AML) compliance** in the Indian financial sector. It ingests regulatory documents (PMLA, RBI circulars, FATF recommendations) and your internal policy documents, then gives you two powerful capabilities:

1. **Regulatory Chatbot** — Ask any question about AML regulations and get precise, cited answers.
2. **Automated Gap Analyzer** — Upload your internal policy and get a structured report showing exactly which regulatory obligations are COVERED, PARTIALLY covered, or MISSING.

---

## Why SIA-RAG is Better Than Ordinary RAG

Most off-the-shelf RAG systems are great for general Q&A. SIA-RAG goes far beyond that. Here is exactly how:

### 1. Hybrid Retrieval — Not Just Keyword Search, Not Just Semantic Search

| Ordinary RAG | SIA-RAG |
|---|---|
| Uses either keyword search OR semantic search | Uses **both simultaneously** and fuses results |
| Fails on exact numbers (e.g., "₹10 lakh limit") | Keyword (BM25) search catches exact numeric thresholds |
| Fails on paraphrased language | Dense vector search catches semantic meaning |

We combine both using **Reciprocal Rank Fusion (RRF)** — a mathematically sound method that merges two ranked lists without needing to calibrate their scores. This pushes Hit@1 from 22.9% (keyword-only) to **60.4%**.

---

### 2. Jurisdiction-Aware Reranking

| Ordinary RAG | SIA-RAG |
|---|---|
| Treats all retrieved documents equally | Prioritizes national law (PMLA/RBI) over international guidelines (FATF) |
| May surface an FATF guideline over a binding RBI mandate | Automatically weights: 80% semantic + 20% jurisdictional authority |

This is critical for AML: a PMLA statutory obligation carries more legal weight than an FATF recommendation. The reranker knows this.

---

### 3. Zero-Hallucination Gap Analysis

| Ordinary RAG | SIA-RAG |
|---|---|
| LLM may cite evidence that doesn't exist in the source | Every cited evidence is **verified by deterministic substring matching** |
| Hallucination rates can be ~15% even with GPT-4o | SIA-RAG achieves **0.0% hallucination rate** |

The LLM judge makes a compliance verdict. Then a hard-coded guard checks: does the quoted evidence actually appear in the policy text? If not, the citation is rejected — no exceptions.

---

### 4. Dual-Pipeline in One System

| Ordinary RAG | SIA-RAG |
|---|---|
| Built for Q&A only | Handles both **Q&A and bulk document auditing** |
| Separate tools needed for different tasks | A single platform, single ingestion pipeline, two smart execution paths |

A user asking a question goes down Path A (Chatbot). A user uploading a policy for audit goes down Path B (Gap Analyzer). The intent router handles the dispatch automatically.

---

### 5. Layout-Aware Document Parsing

| Ordinary RAG | SIA-RAG |
|---|---|
| Treats PDFs as plain text | Preserves document structure (chapters, sections, sub-clauses) |
| Chunks text blindly by character count | Uses **dual-granularity chunking**: sentence-level AND section-level |
| No deduplication | Removes near-duplicate chunks (cosine similarity > 0.95) before indexing |

Regulatory documents are hierarchical. A flat chunker destroys that structure. SIA-RAG's Docling-powered parser keeps it intact.

---

### 6. AML-Domain-Specific Metadata Tagging

Every indexed chunk is automatically tagged with:
- **Regulation type** — KYC, STR, CTR, PEP, EDD, etc.
- **Jurisdiction** — RBI, PMLA, FATF, FIU-IND, SEBI
- **Obligation level** — Mandatory, Recommended, Informational
- **Document tier** — Statutory Law, Regulatory Directive, International Standard

This allows the retriever to filter precisely, not just find semantically similar text.

---

## Results at a Glance

| Metric | BM25 Baseline | SIA-RAG |
|---|---|---|
| Retrieval Hit@1 | 22.9% | **60.4%** |
| Retrieval Hit@5 | 39.6% | **72.9%** |
| Gap Classification Macro F1 | 0.429 | **1.00** |
| Hallucination Rate | N/A | **0.0%** |

---

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+ (for the frontend)
- A [Groq API key](https://console.groq.com) (free tier works)

### 1. Clone & Configure

```bash
git clone <your-repo-url>
cd SIA_RAG_Project
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### 2. Start the Backend

```bash
cd backend
pip install -r requirements.txt
python app.py
```

### 3. Start the Frontend

```bash
cd frontend-next
npm install
npm run dev
```

### 4. Or Use Docker (Recommended)

```bash
docker-compose up --build
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## How to Use

### Regulatory Chatbot
1. Go to the **Chat** page
2. Type any AML compliance question, e.g.:
   - *"What are the KYC requirements for high-risk customers under RBI guidelines?"*
   - *"What is the cash transaction reporting threshold under PMLA?"*
3. Get a cited, verified answer with source references

### Gap Analyzer
1. Go to the **Gap Analyzer** page
2. Upload your internal AML policy PDF
3. Click **Analyze**
4. Get a structured report with:
   - A list of regulatory obligations
   - Status: `COVERED` / `PARTIAL` / `MISSING`
   - Evidence quotes from your policy
   - Recommendations for gaps

---

## Project Structure

```
SIA_RAG_Project/
├── backend/
│   ├── agents/          # LangGraph agent nodes
│   ├── api/             # FastAPI route handlers
│   ├── graph/           # Obligation knowledge graph (NetworkX)
│   ├── ingestion/       # PDF parsing, chunking, AML tagging
│   ├── retrieval/       # Dense, sparse, hybrid retrieval + reranker
│   ├── generation/      # LLM answer synthesis
│   ├── monitoring/      # Evaluation and metrics
│   └── app.py           # FastAPI application entry point
├── frontend-next/       # Next.js frontend application
├── eval/                # Ground-truth evaluation datasets
├── scripts/             # Utility scripts
├── data/                # Raw regulatory PDFs
├── chroma_db/           # Persistent vector store
└── docker-compose.yml
```

---

## Regulatory Documents Covered

| Document | Jurisdiction | Type |
|---|---|---|
| Prevention of Money Laundering Act, 2002 | India (PMLA) | Statutory Law |
| RBI KYC Master Direction, 2016 | India (RBI) | Regulatory Directive |
| FATF 40 Recommendations (2012–2022) | International | International Standard |

---

## Tech Stack Summary

| Layer | Technology |
|---|---|
| LLM | LLaMA 3.3 70B via Groq API |
| Embeddings | all-MiniLM-L6-v2 (local, no API cost) |
| Vector Store | ChromaDB |
| Orchestration | LangGraph |
| Backend API | FastAPI (Python) |
| Frontend | Next.js + Tailwind CSS |
| PDF Parsing | Docling |
| Sparse Search | BM25 (rank_bm25) |
| Reranker | ms-marco-MiniLM-L-6-v2 |

---

## Authors

- **A Allan** — Amrita School of Engineering, Chennai
- **Suriya K S** — Amrita School of Engineering, Chennai
- **Dr. Simhadri Ravishankar** (Supervisor) — Amrita School of Engineering, Chennai

---

## License

This project is developed as an academic research prototype. See [LICENSE](LICENSE) for details.
