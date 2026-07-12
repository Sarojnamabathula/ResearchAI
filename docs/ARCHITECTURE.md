# ResearchAI — System Architecture

## Overview

ResearchAI is a modular, production-quality AI Research Agent built on IBM watsonx. It follows a clean three-tier architecture: a **Streamlit frontend**, a **FastAPI backend**, and a set of **AI analysis modules** that communicate via RESTful endpoints.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    STREAMLIT FRONTEND                           │
│  Home │ Search │ Papers │ Chat │ Compare │ Review │ Gaps │ ...  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP REST
┌──────────────────────────▼──────────────────────────────────────┐
│                    FASTAPI BACKEND                              │
│  /api/search  /api/papers  /api/chat  /api/compare  ...        │
│                                                                 │
│  ┌────────────┐  ┌─────────────┐  ┌──────────────────────────┐ │
│  │  Core      │  │  DB Layer   │  │  API Routes              │ │
│  │  Models    │  │  (SQLite)   │  │  (11 route modules)      │ │
│  │  Exceptions│  │  aiosqlite  │  │                          │ │
│  │  Logger    │  │             │  │                          │ │
│  └────────────┘  └─────────────┘  └──────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                  AI MODULES (15 modules)                        │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Module 1: Query Analyzer                                 │  │
│  │  Module 2: Search Engine (arXiv + S2 + CrossRef parallel) │  │
│  │  Module 3: PDF Processor (PyMuPDF)                        │  │
│  │  Module 4: Knowledge Base / Vector Store                  │  │
│  │  Module 5: RAG Pipeline                                   │  │
│  │  Module 6: Summarizer                                     │  │
│  │  Module 7: Comparator                                     │  │
│  │  Module 8: Literature Review Generator                    │  │
│  │  Module 9: Gap Analyzer                                   │  │
│  │  Module 10: Hypothesis Generator                          │  │
│  │  Module 11: Citation Manager                              │  │
│  │  Module 12: Report Generator                             │  │
│  │  Module 13: Research Chat                                │  │
│  │  Module 14: Timeline Generator                           │  │
│  │  Module 15: Trend Analyzer                               │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│              EXTERNAL SERVICES & STORAGE                        │
│                                                                 │
│  ┌─────────────────────┐  ┌──────────────────────────────────┐  │
│  │  IBM watsonx.ai     │  │  Vector Store                    │  │
│  │  Granite-13b        │  │  ChromaDB (default)              │  │
│  │  (text generation)  │  │  FAISS (alternative)             │  │
│  │  sentence-xfmr      │  │                                  │  │
│  │  (embeddings)       │  │                                  │  │
│  └─────────────────────┘  └──────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  External APIs                                           │   │
│  │  arXiv · Semantic Scholar · CrossRef · PubMed (opt.)    │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### 1. Literature Search Flow

```
User Query (natural language)
    │
    ▼
QueryAnalyzer (IBM Granite)
    │  → topic, domain, keywords, intent
    ▼
SearchEngine (parallel HTTP)
    ├── ArxivSearch
    ├── SemanticScholarSearch
    └── CrossRefSearch
    │
    ▼
Deduplicate + Rank
    │
    ▼
Save to SQLite + Return SearchResult
```

### 2. PDF Processing & Indexing Flow

```
PDF URL or uploaded file
    │
    ▼
PDFProcessor (PyMuPDF)
    │  → title, abstract, sections, chunks
    ▼
VectorStore.add_chunks()
    │  → sentence-transformers embed
    │  → ChromaDB / FAISS persist
    ▼
SQLite save chunks
```

### 3. RAG Chat Flow

```
User Question + Session ID
    │
    ▼
VectorStore.search() — semantic similarity
    │  → Top-K relevant PaperChunks
    ▼
Build context prompt
    │  → chunks + conversation history
    ▼
IBM Granite generate()
    │  → grounded answer
    ▼
ExplainableResponse
    │  → answer + sources + confidence + reasoning
    ▼
Save to chat session
```

---

## Module Dependency Graph

```
WatsonxClient (singleton)
    ├── QueryAnalyzer
    ├── PaperSummarizer
    ├── PaperComparator
    ├── LiteratureReviewGenerator
    │       └── (uses PaperComparator)
    ├── ResearchGapAnalyzer
    ├── HypothesisGenerator
    ├── TimelineGenerator
    ├── TrendAnalyzer
    ├── RAGPipeline
    │       └── KnowledgeBase / VectorStore
    ├── ResearchChatService
    │       └── RAGPipeline
    └── ReportGenerator
            ├── LiteratureReviewGenerator
            ├── PaperComparator
            ├── ResearchGapAnalyzer
            └── CitationManager
```

---

## Database Schema (SQLite)

```sql
papers          — research paper metadata
paper_chunks    — text chunks extracted from PDFs
search_history  — query log
chat_sessions   — multi-turn conversation sessions
reports         — generated research reports
citations       — generated citation strings
```

---

## Configuration

All configuration is managed via environment variables in `.env` (see `.env.example`).

Key settings:
- `WATSONX_API_KEY` / `WATSONX_PROJECT_ID` — IBM watsonx credentials
- `GRANITE_MODEL_ID` — LLM model (default: `ibm/granite-13b-instruct-v2`)
- `VECTOR_STORE_TYPE` — `chromadb` or `faiss`
- `EMBEDDING_DIMENSION` — vector dimensions (default: 768)

---

## Responsible AI Principles

| Principle | Implementation |
|-----------|---------------|
| No hallucinated citations | Citations generated only from real retrieved metadata |
| Transparent sources | Every answer includes `sources_used` and `retrieved_documents` |
| Confidence indication | All AI responses include a `confidence` float [0–1] |
| AI-generated flags | Hypotheses include `is_ai_generated: true` |
| Graceful degradation | Stub responses when watsonx is not configured |
| Data isolation | Each session scoped to its paper set |
