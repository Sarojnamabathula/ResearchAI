# ResearchAI — Installation Guide

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.11+ | pyenv recommended |
| pip | latest | `pip install --upgrade pip` |
| IBM Cloud account | — | Required for watsonx AI generation |

---

## Installation Steps

### Step 1 — Clone the repository

```bash
git clone <your-repo-url>
cd researchai
```

### Step 2 — Create a virtual environment (recommended)

```bash
python -m venv .venv

# Linux/macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

This installs:
- FastAPI + uvicorn
- IBM watsonx-ai SDK
- sentence-transformers
- ChromaDB and FAISS
- PyMuPDF, pdfplumber
- Streamlit + Plotly
- aiosqlite
- All testing dependencies

### Step 4 — Configure environment

```bash
cp .env.example .env
```

Edit `.env` with a text editor and set your IBM watsonx credentials:

```env
WATSONX_API_KEY=your_actual_api_key_here
WATSONX_PROJECT_ID=your_actual_project_id_here
```

#### Getting IBM watsonx credentials

1. Log in at [IBM Cloud Console](https://cloud.ibm.com)
2. Navigate to **Manage → IAM → API Keys**
3. Create a new API key and copy it
4. Navigate to your **watsonx.ai** project → **Manage → General**
5. Copy the **Project ID**

#### Optional API keys (for higher rate limits)

```env
SEMANTIC_SCHOLAR_API_KEY=your_s2_key   # https://www.semanticscholar.org/product/api
PUBMED_API_KEY=your_pubmed_key         # https://www.ncbi.nlm.nih.gov/account/
```

### Step 5 — Run the application

#### Backend only

```bash
python run.py
```

The API will be available at:
- API: http://localhost:8000
- Swagger docs: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

#### Frontend only

```bash
python run.py --frontend
```

The Streamlit app will be at: http://localhost:8501

#### Both together (development)

```bash
python run.py --all
```

---

## Docker Installation

### Prerequisites
- Docker 24+
- Docker Compose v2+

### Steps

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with credentials

# 2. Build and start
docker compose up --build

# 3. Access
# Backend: http://localhost:8000
# Frontend: http://localhost:8501

# 4. Stop
docker compose down

# 5. Stop and remove data volumes
docker compose down -v
```

---

## Verifying the Installation

1. Open http://localhost:8000/api/health
2. You should see:
   ```json
   {"status": "healthy", "version": "1.0.0", "watsonx_configured": true}
   ```
3. `watsonx_configured: false` means credentials are missing in `.env` — the app will use stub responses.

---

## Running Tests

```bash
# Run all tests
pytest

# With coverage report
pytest --cov=researchai --cov-report=term-missing

# Run specific module
pytest tests/test_models.py -v
pytest tests/test_database.py -v
```

> Tests use mocks and do not require real IBM watsonx credentials.

---

## Common Issues

### `ImportError: No module named 'researchai'`

Make sure you're running from the project root and the package is on the Python path:
```bash
pip install -e .   # or
export PYTHONPATH=/path/to/researchai
```

### `chromadb.errors.InvalidCollectionException`

Delete the existing ChromaDB data and restart:
```bash
rm -rf data/embeddings/chroma
python run.py
```

### `WatsonxError: Text generation failed`

Check your credentials in `.env`. Confirm the project ID and API key are correct, and the watsonx.ai service is provisioned in your IBM Cloud account.

### PDF download fails

Some publishers block automated downloads. Use the manual upload feature in the Papers page instead.

---

## Data Storage Locations

| Directory | Contents |
|-----------|---------|
| `data/papers/` | Downloaded PDF files |
| `data/embeddings/chroma/` | ChromaDB vector store |
| `data/embeddings/faiss.index` | FAISS index (if configured) |
| `data/reports/` | Generated report files |
| `data/researchai.db` | SQLite database |
| `data/logs/researchai.log` | Rotating application log |
