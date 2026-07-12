# ResearchAI 🔬

**Intelligent Academic Research Agent powered by IBM watsonx · Granite Models**

ResearchAI is a production-quality AI research assistant that helps researchers, students, educators, and industry professionals throughout the entire research lifecycle — from literature discovery through report generation.

---

## Key Features

| Module | Capability |
|--------|-----------|
| 🔍 **Query Analysis** | AI-powered research question understanding with intent detection |
| 📚 **Literature Search** | Parallel search across arXiv, Semantic Scholar, and CrossRef |
| 📄 **PDF Processing** | Automatic download, extraction, and semantic chunking |
| 🧠 **Knowledge Base** | ChromaDB/FAISS vector store with sentence-transformer embeddings |
| 💬 **RAG Chat** | Multi-turn conversational Q&A grounded in your papers |
| 📝 **Summarization** | Short, medium, and detailed structured paper summaries |
| ⚖️ **Comparison** | Side-by-side comparison tables for 2–10 papers |
| 📖 **Literature Review** | Academic-quality survey generation with thematic sections |
| 🔎 **Gap Analysis** | Identifies underexplored topics, missing datasets, weak methods |
| 💡 **Hypothesis Generator** | AI-suggested novel research directions with evaluation methods |
| 📜 **Citation Manager** | APA, IEEE, MLA, Chicago, BibTeX — never fabricated |
| 📊 **Report Generator** | Full structured research reports, Markdown export |
| 📅 **Research Timeline** | Chronological field evolution with visual chart |
| 📈 **Trend Analysis** | Publication trends, keyword frequency, top authors/venues |
| 🧩 **Explainable AI** | Every answer includes sources, confidence, and reasoning |

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| **AI** | IBM watsonx.ai — Granite 13B Instruct v2 |
| **Embeddings** | sentence-transformers/all-MiniLM-L6-v2 |
| **Vector Store** | ChromaDB (default) / FAISS |
| **Backend** | Python 3.11 · FastAPI · uvicorn |
| **Frontend** | Streamlit (11 pages) · Plotly |
| **Database** | SQLite · aiosqlite |
| **PDF** | PyMuPDF · pdfplumber |
| **Search APIs** | arXiv · Semantic Scholar · CrossRef |
| **Deployment** | Docker · Docker Compose |

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- IBM Cloud account with watsonx.ai access
- Git

### 2. Install

```bash
git clone <your-repo-url>
cd researchai
pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
```

Edit `.env` and set:
```env
WATSONX_API_KEY=your_ibm_cloud_api_key
WATSONX_PROJECT_ID=your_watsonx_project_id
```

> **Note:** The application runs in stub mode without credentials, returning placeholder responses so you can explore the interface.

### 4. Run

```bash
# Backend only (FastAPI)
python run.py

# Frontend only (Streamlit)
python run.py --frontend

# Both together
python run.py --all
```

- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/api/docs
- **Frontend:** http://localhost:8501

---

## Docker Deployment

```bash
# Copy and configure environment
cp .env.example .env
# Edit .env with your credentials

# Build and start all services
docker compose up --build

# Stop
docker compose down
```

Services:
- Backend: http://localhost:8000
- Frontend: http://localhost:8501

---

## Project Structure

```
researchai/
├── backend/
│   ├── api/
│   │   └── routes/          # 11 FastAPI route modules
│   ├── core/
│   │   ├── models.py         # 30+ Pydantic domain models
│   │   ├── watsonx_client.py # IBM Granite integration (singleton)
│   │   ├── exceptions.py     # Typed exception hierarchy
│   │   └── logger.py         # Rotating file + console logger
│   ├── db/
│   │   └── database.py       # Async SQLite CRUD (aiosqlite)
│   ├── modules/
│   │   ├── search/           # Query analysis + 3 search providers
│   │   ├── processing/       # PDF download, extract, chunk
│   │   ├── knowledge_base/   # Vector store (ChromaDB / FAISS)
│   │   ├── rag/              # Retrieval-Augmented Generation
│   │   ├── summarization/    # Structured paper summaries
│   │   ├── comparison/       # Multi-paper comparison
│   │   ├── literature_review/# Academic review generation
│   │   ├── gap_analysis/     # Gap + hypothesis generation
│   │   ├── citation/         # 5-format citation manager
│   │   ├── report/           # Full report orchestration
│   │   ├── chat/             # Session-based RAG chat
│   │   ├── timeline/         # Chronological timeline
│   │   └── trends/           # Bibliometric trend analysis
│   └── main.py               # FastAPI app entry point
├── config/
│   └── settings.py           # All configuration (env vars)
├── frontend/
│   ├── app.py                # Home page + shared state
│   └── pages/                # 11 Streamlit pages
│       ├── 1_Search.py
│       ├── 2_Papers.py
│       ├── 3_Chat.py
│       ├── 4_Compare.py
│       ├── 5_Literature_Review.py
│       ├── 6_Gap_Analysis.py
│       ├── 7_Citations.py
│       ├── 8_Reports.py
│       ├── 9_Timeline.py
│       ├── 10_Trends.py
│       └── 11_Settings.py
├── tests/
│   ├── conftest.py
│   ├── test_models.py
│   ├── test_search_engine.py
│   ├── test_database.py
│   ├── test_citation_manager.py
│   ├── test_watsonx_client.py
│   ├── test_query_analyzer.py
│   └── test_api_routes.py
├── docs/
│   ├── ARCHITECTURE.md       # System architecture + data flows
│   └── API.md                # Full API reference
├── data/                     # Auto-created runtime data
│   ├── papers/               # Downloaded PDFs
│   ├── embeddings/           # ChromaDB / FAISS index
│   ├── reports/              # Generated reports
│   └── researchai.db         # SQLite database
├── .env.example
├── requirements.txt
├── pytest.ini
├── Dockerfile
├── docker-compose.yml
└── run.py                    # Launcher script
```

---

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=researchai --cov-report=term-missing

# Run a specific test file
pytest tests/test_models.py -v
```

> Most tests run without IBM watsonx credentials by using mocks and stub responses.

---

## API Quick Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/search` | POST | Multi-source literature search |
| `/api/search/analyze` | GET | Query analysis only |
| `/api/papers` | GET | List indexed papers |
| `/api/papers/{id}` | DELETE | Delete a paper |
| `/api/papers/process` | POST | Download + index PDF |
| `/api/papers/upload` | POST | Upload local PDF |
| `/api/summarize` | POST | Generate paper summary |
| `/api/compare` | POST | Compare multiple papers |
| `/api/review` | POST | Generate literature review |
| `/api/gaps/analyze` | POST | Identify research gaps |
| `/api/gaps/hypotheses` | POST | Generate hypotheses |
| `/api/citations/generate` | POST | Generate citations |
| `/api/reports/generate` | POST | Generate research report |
| `/api/chat/session` | POST | Create chat session |
| `/api/chat/message` | POST | Send chat message |
| `/api/timeline/generate` | POST | Generate research timeline |
| `/api/trends/analyze` | POST | Analyse publication trends |

Full API reference: [`docs/API.md`](docs/API.md)

---

## Responsible AI

ResearchAI is designed with transparency and reliability at its core:

- **No fabricated citations** — citations are generated only from real retrieved metadata
- **Source attribution** — every AI response includes `sources_used` and `retrieved_documents`  
- **Confidence scores** — all responses include a calibrated confidence float [0–1]
- **AI-generated flags** — hypotheses are clearly marked `is_ai_generated: true`
- **Graceful degradation** — informative stub responses when credentials are absent
- **Explainability** — every answer includes a `reasoning_summary`

---

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `WATSONX_API_KEY` | — | IBM Cloud API key |
| `WATSONX_PROJECT_ID` | — | watsonx.ai project ID |
| `WATSONX_URL` | `https://us-south.ml.cloud.ibm.com` | watsonx endpoint |
| `GRANITE_MODEL_ID` | `ibm/granite-13b-instruct-v2` | LLM model |
| `VECTOR_STORE_TYPE` | `chromadb` | `chromadb` or `faiss` |
| `MAX_NEW_TOKENS` | `1024` | Max generation tokens |
| `TEMPERATURE` | `0.7` | Sampling temperature |
| `CHUNK_SIZE` | `512` | PDF chunk size (words) |
| `TOP_K_RESULTS` | `5` | Top-K for RAG retrieval |
| `SEARCH_RESULTS_LIMIT` | `20` | Max results per search |

Full reference: [`.env.example`](.env.example)

---

## Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for:
- Full system diagram
- Data flow diagrams for search, PDF processing, and RAG
- Module dependency graph
- Database schema
- Responsible AI principles

---

## License

MIT License — see LICENSE file for details.

---

*ResearchAI — Built with IBM watsonx · Demonstrating enterprise-grade AI engineering for research productivity.*
