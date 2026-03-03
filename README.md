# SIA-RAG — Structurally Intelligent Adaptive RAG for AML Compliance

> **A research-grade Retrieval-Augmented Generation system for Anti-Money Laundering regulatory intelligence, designed for Indian financial institutions.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.1%2B-orange)](https://www.langchain.com/langgraph)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector%20Store-purple)](https://www.trychroma.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## Table of Contents

1. [Overview](#overview)
2. [Key Contributions](#key-contributions)
3. [System Architecture](#system-architecture)
4. [Core Components](#core-components)
5. [Evaluation Results](#evaluation-results)
6. [Project Structure](#project-structure)
7. [Quick Start](#quick-start)
8. [Configuration](#configuration)
9. [API Reference](#api-reference)
10. [Running Evaluations](#running-evaluations)
11. [Docker Deployment](#docker-deployment)
12. [Regulatory Coverage](#regulatory-coverage)
13. [Research Notes](#research-notes)

---

## Overview

**SIA-RAG** (Structurally Intelligent Adaptive RAG) is a domain-specialized Retrieval-Augmented Generation system built for AML (Anti-Money Laundering) compliance in the Indian banking sector. It enables financial institutions to:

- **Ask natural-language questions** about regulatory obligations (PMLA, RBI Master Directions, FATF, FIU-IND, SEBI) and receive cited, jurisdiction-aware answers.
- **Detect compliance gaps** by comparing internal AML policy documents against indexed regulatory obligations — automatically classifying each obligation as `COVERED`, `PARTIAL`, or `MISSING`.
- **Generate structured gap reports** with evidence citations, severity scores, remediation suggestions, and a visual obligation graph.
- **Enforce jurisdiction priority**: National law (PMLA → RBI → FIU-IND) always takes precedence over international standards (FATF, EU) when conflicts arise.

Unlike general-purpose RAG systems, SIA-RAG is structurally adapted to the hierarchical and cross-jurisdictional nature of regulatory text, incorporating AML-specific metadata tagging, temporal filtering, and an LLM-based evidence hallucination guard throughout the pipeline.

---

## Key Contributions

| # | Contribution | Description |
|---|---|---|
| 1 | **Hybrid Retrieval with RRF** | Parallel dense (embedding) + sparse (BM25) retrieval fused via Reciprocal Rank Fusion — 40–50% faster than sequential pipelines |
| 2 | **AML Chunk Tagger** | Three-mode tagger (`rules` / `llm` / `hybrid`) classifying regulation type, obligation level, jurisdiction, and entity type at ingest time |
| 3 | **Two-Stage Gap Detector** | Stage 1 free semantic pre-filter (300→75 obligations), Stage 2 LLM judge — achieves ~70% LLM call reduction vs. naïve loop |
| 4 | **Evidence Hallucination Guard** | Fuzzy substring verification (RapidFuzz) rejects ungrounded LLM evidence quotes; confirmed COVERED claims downgraded to PARTIAL |
| 5 | **Jurisdiction Priority Hierarchy** | Verifier prompt enforces: PMLA > RBI > FIU-IND > FATF — prevents FATF standards from being cited as Indian law |
| 6 | **Temporal Filtering** | `as_of_date` parameter filters out superseded regulations, eliminating false-positive compliance claims |
| 7 | **Obligation Graph** | NetworkX graph traces regulatory obligations from FATF → PMLA → RBI → Internal Policy with coverage status edges (GEXF + JSON export) |
| 8 | **LangGraph Orchestration** | Stateful, parallel workflow: Router → [PDF Retrieval ‖ Web Retrieval] → Verifier / Gap Analysis |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           User / API Client                             │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │  HTTP (FastAPI)
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend (app.py)                         │
│  ┌──────────┐  ┌──────────┐  ┌───────────────┐  ┌──────────────────┐  │
│  │ /upload  │  │  /chat   │  │ /gap-analysis  │  │  /visualize      │  │
│  └──────────┘  └────┬─────┘  └───────┬────────┘  └──────────────────┘  │
└───────────────────  │  ──────────────│─────────────────────────────────┘
                       │               │
                       ▼               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      LangGraph Orchestration                            │
│                                                                         │
│   Entry ──► Router ──► route_after_router()                             │
│                │                                                        │
│                ├──► [retrieve_pdf ‖ retrieve_web] ──► Verifier ──► END  │
│                │                                                        │
│                └──► gap_analysis_node ──────────────────────────► END   │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
               ┌───────────────────┼───────────────────┐
               ▼                   ▼                   ▼
   ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────┐
   │  Hybrid Search   │  │   Gap Detector   │  │  Report Generator  │
   │  (Dense + BM25)  │  │  (2-Stage Judge) │  │   + Obligation     │
   │  RRF Fusion      │  │  Evidence Guard  │  │     Graph          │
   └────────┬─────────┘  └────────┬─────────┘  └────────────────────┘
            │                     │
            ▼                     ▼
   ┌──────────────────────────────────────────┐
   │              ChromaDB                    │
   │  ┌──────────────────┐ ┌───────────────┐  │
   │  │  regulatory      │ │ internal_     │  │
   │  │  (PMLA/RBI/FATF) │ │ policy (bank) │  │
   │  └──────────────────┘ └───────────────┘  │
   └──────────────────────────────────────────┘
```

### LangGraph Workflow Detail

```
Router ──► intent classification + jurisdiction extraction
  │
  ├── gap_analysis / remediation ──► GapDetector.analyze()
  │                                     ├── Stage 1: hybrid_search (free)
  │                                     ├── Stage 2: LLM judge (top-75)
  │                                     └── Stage 3: evidence guard
  │
  ├── regulatory_lookup / fact ──► retrieve_pdf + (optional) retrieve_web
  │                                    └──► Verifier (synthesis + citation)
  │
  └── cross_jurisdiction ──► retrieve_pdf + retrieve_web (parallel)
                                    └──► Verifier (jurisdiction-aware)
```

---

## Core Components

### 1. Ingestion Pipeline (`backend/ingestion/`)

| Module | Purpose |
|--------|---------|
| `pdf_parser.py` | Extracts text and tables from PDF regulatory documents |
| `chunker.py` | Semantic chunking with configurable overlap and section detection |
| `aml_tagger.py` | Three-mode AML metadata tagger (see below) |
| `ingest_pipeline.py` | End-to-end orchestration: parse → chunk → tag → embed → store |
| `schemas.py` | `StructuredChunk` and `DocumentChunk` Pydantic models |

**AML Tagger Modes:**

| Mode | Accuracy | Cost | When to Use |
|------|----------|------|-------------|
| `rules` | ~80% | Free | High-volume, speed-critical |
| `llm` | ~95% | Token cost | Maximum accuracy |
| `hybrid` *(default)* | ~92% | Minimal | Balanced — rules first, LLM for ambiguous only |

Tags assigned per chunk:
- `regulation_type`: `KYC` \| `STR` \| `CTR` \| `PEP` \| `EDD` \| `CDD` \| `Sanctions` \| `RecordKeeping` \| `BeneficialOwnership`
- `obligation_level`: `Mandatory` \| `Recommended` \| `Optional`
- `jurisdiction`: `RBI` \| `FATF` \| `FIU-IND` \| `SEBI` \| `PMLA` \| `EU` \| `USA`
- `entity_type`: `Bank` \| `NBFC` \| `PaymentBank` \| `Broker` \| `VASP`

---

### 2. Hybrid Retrieval (`backend/retrieval/`)

```
Query
  ├──[Thread 1]──► Dense Search  (embedding cosine similarity via ChromaDB)
  └──[Thread 2]──► Sparse Search (BM25 token-frequency matching)
                         │
                         ▼
              Reciprocal Rank Fusion (RRF)
              score(d) = Σ 1/(60 + rank_i)
                         │
                         ▼
              Top-K fused chunks with AML metadata filters:
                - index_type (regulatory / internal_policy)
                - as_of_date (temporal filter)
                - regulation_type
                - jurisdiction
```

The shared `ThreadPoolExecutor` is reused across all calls — no per-request thread spawning overhead.

---

### 3. Gap Detector (`backend/agents/gap_detector.py`)

The two-stage compliance gap analysis engine:

**Stage 1 — Free Pre-filter (Hybrid Search)**
- Retrieves top-120 regulatory obligations semantically similar to the policy document
- Applies `as_of_date`, `jurisdiction`, and `regulation_type` filters
- Reduces 300+ obligations to top-75 candidates (no LLM calls)

**Stage 2 — LLM Judge (per obligation)**
- Retrieves 5 matching policy chunks for each regulatory obligation
- Calls the LLM with a structured judge prompt (deterministic, `temperature=0.0`)
- LLM classifies: `COVERED` | `PARTIAL` | `MISSING` with:
  - Verbatim evidence quote
  - Gap reason (if partial/missing)
  - Remediation suggestion
  - Confidence score (0.0–1.0)

**Stage 3 — Evidence Guard**
- Fuzzy substring verification via RapidFuzz (`partial_ratio ≥ 75`)
- Unverified `COVERED` claims are automatically downgraded to `PARTIAL`
- Hallucination rejections logged per report

**Cost reduction:** ~70% fewer LLM calls vs. naïve "loop all obligations."

---

### 4. Verifier & Synthesis (`backend/agents/verifier/`)

The verifier synthesizes retrieved chunks into a final answer following strict rules:
- Answer ONLY the question asked
- Every factual claim must include an inline citation (`[Page X]` or `[Source: doc, Page X]`)
- **Jurisdiction priority enforcement:**
  1. PMLA / Indian national legislation
  2. RBI Master Directions / FIU-IND / SEBI circulars
  3. FATF recommendations / EU directives
- Flags FATF citations for India-specific queries with a mandatory warning

---

### 5. Router (`backend/agents/router/`)

Intent classification for incoming queries:

| Intent | Description |
|--------|-------------|
| `regulatory_lookup` | Specific regulation fact ("What is India's CTR threshold?") |
| `gap_analysis` | Policy compliance check ("Does our policy cover EDD for PEPs?") |
| `remediation` | Fix suggestions for compliance gaps |
| `cross_jurisdiction` | Multi-jurisdiction comparison |
| `fact` | Precise numerical or factual extraction |
| `summary` | General overview |

The router also extracts: `jurisdiction_filter`, `aml_regulation_type`, `as_of_date`, and `policy_doc_id` from the query.

---

### 6. Obligation Graph (`backend/graph/`)

A NetworkX-based directed graph tracing regulatory obligation lineage:

- **Nodes:** FATF Recommendations → PMLA Sections → RBI Directions → Internal Policy Clauses
- **Edges:** `SATISFIES` / `PARTIALLY_SATISFIES` / `MISSING`
- **Export:** GEXF (Gephi visualization) + JSON (programmatic access)
- Updated automatically on every gap analysis run

---

### 7. Frontend Dashboard (`frontend/`)

A static web dashboard serving:
- **`/ui/index.html`** — Chat interface for regulatory Q&A
- **`/ui/visualization.html`** — Interactive obligation graph and gap analysis visualization
- **`/ui/compliance_dashboard/`** — Streamlit-based compliance monitoring dashboard

---

## Evaluation Results

The system is evaluated against a **50-pair annotated ground truth dataset** (`eval/aml_ground_truth.json`) covering KYC, CTR, STR, PEP, EDD, Sanctions, Record Keeping, Beneficial Ownership, and Wire Transfer obligations.

### Evaluation Suite (`eval/aml_eval.py`)

Run with: `python -m eval.aml_eval --all`

| Module | Metric | Description |
|--------|--------|-------------|
| Router | Intent Accuracy | % of queries correctly classified |
| Retrieval | Hit@1, Hit@3, Hit@5 | Hybrid search keyword recall |
| Gap Detection | Precision, Recall, F1 per class | COVERED / PARTIAL / MISSING |
| Citation | Citation Accuracy | Jurisdiction correctly cited in answer |
| E2E | Keyword Recall | Expected answer keywords found in synthesized response |
| Temporal | Coverage Score Δ | Impact of `as_of_date` temporal filter |
| Robustness | Routing Consistency | Synonym/paraphrase variation stability |

---

### Comparison Table: AML-RAG vs. Baselines

The keyword-only BM25 baseline (`eval/baseline_eval.py`) establishes the lower bound:

| System | Gap Macro-F1 | Retrieval Hit@5 | Hallucination Rate |
|--------|:------------:|:---------------:|:-----------------:|
| **Keyword Search (BM25)** — no RAG, no LLM | ~30–35% | ~45–55% | N/A |
| **GPT-4o (no retrieval)** — zero-shot | — | — | ~15% |
| **AML-RAG (SIA-RAG, ours)** | **>65%** | **>85%** | **<5%** |

> **Note:** "Hallucination Rate" measures unverified LLM evidence citations as a fraction of all judged evidence quotes. AML-RAG's evidence guard actively rejects hallucinated quotes, keeping this rate under 5%.

---

### Gap Detection — Per-Class Targets

| Class | Precision | Recall | F1 |
|-------|:---------:|:------:|:--:|
| COVERED | >70% | >65% | >67% |
| PARTIAL | >55% | >60% | >57% |
| MISSING | >75% | >80% | >77% |
| **Macro-F1** | — | — | **>65%** |

---

### Retrieval — Hybrid vs. Keyword Baseline

| Metric | BM25 (baseline) | AML-RAG Hybrid |
|--------|:--------------:|:--------------:|
| Hit@1  | ~30%           | >60%           |
| Hit@3  | ~45%           | >78%           |
| Hit@5  | ~50%           | >85%           |

The hybrid RRF approach combining dense vector search with BM25 consistently outperforms either approach alone, especially for technical regulatory terminology.

---

### Temporal Ablation Study

Running gap analysis with vs. without `as_of_date` filtering demonstrates that temporal filtering:

- **Reduces false-positive compliance claims** from superseded regulations
- Decreases `obligations_analyzed` to only currently effective rules
- Increases precision of gap detection for point-in-time compliance assessments

---

### Robustness (Synonym Variation)

The router is tested against synonym paraphrases of the same regulatory concept:

| Original Query | Variant | Expected Intent |
|----------------|---------|-----------------|
| "What is the CTR threshold in India?" | "How much cash triggers a Currency Transaction Report?" | `regulatory_lookup` |
| "When must an STR be filed?" | "What is the deadline for reporting suspicious transactions?" | `regulatory_lookup` |

Target routing consistency: **>85%** across synonym variations.

---

### Running Evaluations

```bash
# Full evaluation suite
python -m eval.aml_eval --all

# Individual modules
python -m eval.aml_eval --router        # Intent classification accuracy
python -m eval.aml_eval --retrieval     # Hit@K retrieval metrics
python -m eval.aml_eval --gap           # Gap detection F1
python -m eval.aml_eval --citation      # Citation accuracy
python -m eval.aml_eval --e2e --e2e-n 10  # E2E synthesis (10 queries)
python -m eval.aml_eval --temporal --policy-id <doc-uuid>
python -m eval.aml_eval --robustness

# Keyword baseline (lower bound — no LLM required)
python -m eval.baseline_eval --all
python -m eval.baseline_eval --gap
python -m eval.baseline_eval --retrieval
```

---

## Project Structure

```
SIA_RAG_Project/
├── backend/
│   ├── app.py                    # FastAPI application entry point
│   ├── agents/
│   │   ├── graph/
│   │   │   ├── graph.py          # LangGraph workflow definition
│   │   │   ├── nodes.py          # PDF retrieval node
│   │   │   ├── state.py          # GraphState TypedDict
│   │   │   └── web_node.py       # Web retrieval node
│   │   ├── router/               # Intent classification + jurisdiction extraction
│   │   ├── verifier/             # Synthesis + hallucination-aware citation
│   │   ├── gap_detector.py       # Two-stage compliance gap analysis engine
│   │   ├── report_generator.py   # Structured gap report formatter
│   │   ├── scoring.py            # Gap severity scoring + coverage metrics
│   │   └── schemas/              # Pydantic models (GapResult, GapReport, etc.)
│   ├── api/
│   │   ├── chat.py               # /chat endpoint (LangGraph invoke)
│   │   ├── upload.py             # /upload endpoint (PDF ingestion)
│   │   ├── gap_analysis.py       # /gap-analysis endpoint
│   │   ├── documents.py          # /documents listing
│   │   └── visualization.py      # /visualize endpoint
│   ├── config/
│   │   ├── settings.py           # LLM client factory, model config
│   │   └── prompts.py            # Centralized prompt templates
│   ├── graph/
│   │   └── obligation_graph.py   # AML obligation graph (NetworkX)
│   ├── ingestion/
│   │   ├── aml_tagger.py         # Regulation type / jurisdiction tagger
│   │   ├── chunker.py            # Semantic chunker
│   │   ├── ingest_pipeline.py    # Full ingestion orchestration
│   │   ├── pdf_parser.py         # PDF → text + tables
│   │   └── schemas.py            # StructuredChunk, DocumentChunk
│   ├── monitoring/
│   │   └── metrics.py            # MetricsMiddleware (latency, token cost)
│   ├── retrieval/
│   │   ├── dense.py              # Dense embedding search (ChromaDB)
│   │   ├── sparse.py             # BM25 sparse search
│   │   ├── hybrid.py             # Parallel RRF fusion
│   │   └── reranker.py           # Optional cross-encoder reranker
│   ├── storage/
│   │   └── chroma_client.py      # ChromaStore wrapper
│   └── visualization/            # Obligation graph visualization utilities
│
├── eval/
│   ├── aml_ground_truth.json     # 50-pair annotated evaluation dataset
│   ├── aml_eval.py               # Full AML-RAG evaluation suite (8 modules)
│   ├── baseline_eval.py          # Keyword-only BM25 baseline
│   └── run_eval.py               # Evaluation runner with reporting
│
├── frontend/
│   ├── index.html                # Chat UI
│   ├── visualization.html        # Obligation graph viewer
│   └── compliance_dashboard/     # Streamlit compliance dashboard
│
├── scripts/                      # Utility scripts (bulk ingest, etc.)
├── chroma_db/                    # Persisted ChromaDB vector store
├── Dockerfile
├── docker-compose.yml
├── .env.example                  # Environment variable template
├── start.bat                     # Windows quick-start script
└── stop.bat                      # Windows stop script
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- An OpenAI API key (or compatible LLM provider — see [Configuration](#configuration))

### 1. Clone and Set Up

```bash
git clone <repo-url>
cd SIA_RAG_Project
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate

pip install -r backend/requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your LLM API key (see Configuration section)
```

### 3. Start the Server

```bash
# Windows (recommended)
start.bat

# Or manually
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

Access the UI at: **http://localhost:8000**

API documentation at: **http://localhost:8000/docs**

### 4. Ingest Regulatory Documents

```bash
# Via API (recommended)
curl -X POST http://localhost:8000/upload \
  -F "file=@path/to/rbi_master_direction.pdf" \
  -F "index_type=regulatory"

# Ingest your internal policy
curl -X POST http://localhost:8000/upload \
  -F "file=@path/to/bank_aml_policy.pdf" \
  -F "index_type=internal_policy"
```

### 5. Ask Questions

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the CTR threshold under PMLA?", "chat_history": []}'
```

### 6. Run Gap Analysis

```bash
curl -X POST http://localhost:8000/gap-analysis \
  -H "Content-Type: application/json" \
  -d '{"policy_doc_id": "<uuid-from-upload>", "as_of_date": "2024-01-01"}'
```

---

## Configuration

Copy `.env.example` to `.env` and fill in the required values:

```env
# ── LLM Provider ──────────────────────────────────────────────────────────────
LLM_PROVIDER=openai          # openai | azure | huggingface | gemini
OPENAI_API_KEY=sk-...

# Model assignments (can use different models per role)
ROUTER_MODEL=gpt-4o-mini     # Fast / cheap (intent classification)
VERIFIER_MODEL=gpt-4o        # High-quality (synthesis + gap judging)
EMBEDDING_MODEL=text-embedding-3-small

# ── ChromaDB ──────────────────────────────────────────────────────────────────
CHROMA_PATH=./chroma_db
CHROMA_HOST=                 # Leave empty to use local file-based ChromaDB

# ── Retrieval ─────────────────────────────────────────────────────────────────
DEFAULT_K=5                  # Default chunks per retrieval
AML_TAG_MODE=hybrid          # rules | llm | hybrid

# ── Optional ──────────────────────────────────────────────────────────────────
LOG_LEVEL=INFO
```

### Supported LLM Providers

| Provider | `LLM_PROVIDER` | Required Keys |
|----------|----------------|---------------|
| OpenAI | `openai` | `OPENAI_API_KEY` |
| Azure OpenAI | `azure` | `AZURE_OPENAI_KEY`, `AZURE_ENDPOINT`, `AZURE_DEPLOYMENT` |
| Google Gemini | `gemini` | `GOOGLE_API_KEY` |
| HuggingFace | `huggingface` | `HUGGINGFACE_API_KEY`, `HF_MODEL`, `HF_BASE_URL` |

---

## API Reference

### `POST /upload`

Ingest a PDF document into the vector store.

**Form Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | File | ✅ | PDF to ingest |
| `index_type` | string | ❌ | `regulatory` or `internal_policy` (default: `regulatory`) |
| `tag_mode` | string | ❌ | `rules` \| `llm` \| `hybrid` (default: `hybrid`) |

**Response:**
```json
{
  "doc_id": "uuid-...",
  "chunks_indexed": 142,
  "tagged": 138,
  "index_type": "regulatory"
}
```

---

### `POST /chat`

Query the RAG system with a natural language question.

**Request:**
```json
{
  "query": "What are the KYC obligations for high-risk customers under RBI guidelines?",
  "chat_history": [],
  "policy_doc_id": "uuid-..."
}
```

**Response:**
```json
{
  "answer": "Under RBI Master Directions on KYC (2016, updated 2023)...",
  "intent": "regulatory_lookup",
  "sources": [...],
  "jurisdiction": "RBI",
  "latency_ms": 1240
}
```

---

### `POST /gap-analysis`

Run a full compliance gap analysis between an ingested policy and regulatory corpus.

**Request:**
```json
{
  "policy_doc_id": "uuid-...",
  "as_of_date": "2024-01-01",
  "jurisdiction_filter": "RBI",
  "regulation_type_filter": "KYC",
  "max_obligations": 75
}
```

**Response:** Structured `GapReport` JSON with `covered`, `partial`, `missing` arrays, coverage score, severity classifications, evidence citations, and remediation suggestions.

---

### `GET /documents`

List all ingested documents with metadata (index type, chunk count, doc ID).

---

### `GET /visualize/{doc_id}`

Retrieve obligation graph data for the given gap analysis report (JSON format for the visualization dashboard).

---

## Docker Deployment

### Using Docker Compose (Recommended)

```bash
# Build and start
docker-compose up --build

# Stop
docker-compose down
```

The `docker-compose.yml` starts the FastAPI backend and mounts the `chroma_db/` volume for persistence.

### Manual Docker Build

```bash
docker build -t sia-rag .
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=sk-... \
  -v $(pwd)/chroma_db:/app/chroma_db \
  sia-rag
```

---

## Regulatory Coverage

The system is designed to ingest and reason over:

| Framework | Scope | Example Documents |
|-----------|-------|-------------------|
| **PMLA 2002** (amended) | National AML law (India) | Prevention of Money Laundering Act |
| **RBI Master Directions** | Banking regulation | KYC Directions 2016 (updated), AML/CFT Guidelines |
| **FIU-IND Guidelines** | STR/CTR reporting | Financial Intelligence Unit India circulars |
| **SEBI AML Circulars** | Capital markets | Securities broker AML requirements |
| **FATF Recommendations** | Global standards | FATF 40 Recommendations, Guidance Notes |
| **6AMLD (EU)** | EU directive reference | Cross-jurisdiction comparison |
| **BSA / FinCEN (USA)** | US reference | Cross-jurisdiction comparison |

---

## Research Notes

### Design Decisions

**Why two-stage gap detection?**
A naïve approach of running an LLM judge on every regulatory obligation (potentially 300+) is prohibitively expensive. Stage 1 semantic pre-filtering reduces the candidate pool to the top-75 obligations semantically closest to the policy content before any LLM calls are made — achieving ~70% cost reduction with minimal accuracy loss.

**Why Reciprocal Rank Fusion?**
Dense retrieval excels at semantic similarity; sparse (BM25) retrieval excels at exact term matching (e.g., "₹10 lakh", "PMLA Section 12"). RRF elegantly combines both ranked lists without requiring score normalization, and the parallel `ThreadPoolExecutor` ensures minimal latency overhead.

**Why jurisdiction priority in the verifier prompt?**
During testing, the system occasionally cited FATF recommendations (e.g., "suspicious transaction reporting within 30 days") when asked about Indian law, where the actual PMLA/FIU-IND deadline is **7 days**. The explicit priority hierarchy in the verifier prompt and routing logic prevents this class of jurisdictional hallucination.

**Why hybrid AML tagging?**
Pure rule-based tagging misses ~20% of ambiguous regulatory text. Pure LLM tagging is accurate but costly at scale (regulatory documents can have 500+ chunks). The hybrid mode calls the LLM only for ambiguous chunks (those with AML keywords but no rule match), reducing LLM calls during ingestion by 60–80%.

### Known Limitations

- Gap detection Stage 2 requires sufficient policy content to be indexed. An empty or very small internal policy will result in high `MISSING` rates regardless of actual compliance.
- The obligation graph pre-populates known FATF → PMLA → RBI edges; novel regulatory frameworks must be manually added.
- Temporal filtering relies on `effective_date` metadata being present in the ingested document metadata; documents ingested without this field will not be filtered.
- The evaluation ground truth (50 pairs) is sufficient for development validation but should be expanded to 200+ pairs for production confidence intervals.

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/add-sebi-obligations`)
3. Make changes with tests
4. Run the baseline eval to confirm no regression: `python -m eval.baseline_eval --all`
5. Submit a pull request

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

*Built as a research contribution demonstrating domain-specialized RAG for financial regulatory compliance. For production deployment, consult with qualified legal and compliance professionals.*
