"""
ResearchAI — Configuration Settings
All environment variables and application settings are managed here.
Copy .env.example to .env and fill in your credentials.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env from project root
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    # ------------------------------------------------------------------ App
    APP_NAME: str = "ResearchAI"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = (
        "Intelligent AI Research Agent powered by IBM watsonx"
    )
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # --------------------------------------------------------------- IBM watsonx
    WATSONX_API_KEY: str = os.getenv("WATSONX_API_KEY", "")
    WATSONX_PROJECT_ID: str = os.getenv("WATSONX_PROJECT_ID", "")
    WATSONX_URL: str = os.getenv(
        "WATSONX_URL", "https://us-south.ml.cloud.ibm.com"
    )

    # IBM Granite model identifiers
    GRANITE_MODEL_ID: str = os.getenv(
        "GRANITE_MODEL_ID", "ibm/granite-13b-instruct-v2"
    )
    GRANITE_EMBEDDING_MODEL: str = os.getenv(
        "GRANITE_EMBEDDING_MODEL", "ibm/slate-125m-english-rtrvr"
    )

    # Model generation parameters
    MAX_NEW_TOKENS: int = int(os.getenv("MAX_NEW_TOKENS", "1024"))
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.7"))
    TOP_P: float = float(os.getenv("TOP_P", "0.9"))
    TOP_K: int = int(os.getenv("TOP_K", "50"))
    REPETITION_PENALTY: float = float(os.getenv("REPETITION_PENALTY", "1.1"))

    # ----------------------------------------------------------------- Paths
    DATA_DIR: Path = BASE_DIR / "data"
    PAPERS_DIR: Path = DATA_DIR / "papers"
    EMBEDDINGS_DIR: Path = DATA_DIR / "embeddings"
    REPORTS_DIR: Path = DATA_DIR / "reports"
    DB_PATH: Path = DATA_DIR / "researchai.db"

    # --------------------------------------------------------- Vector Store
    VECTOR_STORE_TYPE: str = os.getenv("VECTOR_STORE_TYPE", "chromadb")
    CHROMA_PERSIST_DIR: str = str(BASE_DIR / "data" / "embeddings" / "chroma")
    FAISS_INDEX_PATH: str = str(BASE_DIR / "data" / "embeddings" / "faiss.index")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "768"))
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "512"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "64"))
    TOP_K_RESULTS: int = int(os.getenv("TOP_K_RESULTS", "5"))

    # ----------------------------------------------------------- API Sources
    ARXIV_BASE_URL: str = "http://export.arxiv.org/api/query"
    SEMANTIC_SCHOLAR_BASE_URL: str = "https://api.semanticscholar.org/graph/v1"
    SEMANTIC_SCHOLAR_API_KEY: str = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
    CROSSREF_BASE_URL: str = "https://api.crossref.org/works"
    PUBMED_BASE_URL: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    PUBMED_API_KEY: str = os.getenv("PUBMED_API_KEY", "")

    # --------------------------------------------------------- Rate Limiting
    SEARCH_RESULTS_LIMIT: int = int(os.getenv("SEARCH_RESULTS_LIMIT", "20"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    MAX_PDF_SIZE_MB: int = int(os.getenv("MAX_PDF_SIZE_MB", "50"))

    # ---------------------------------------------------------------- CORS
    ALLOWED_ORIGINS: list = ["*"]

    def ensure_dirs(self) -> None:
        """Create required data directories if they do not exist."""
        for d in [
            self.DATA_DIR,
            self.PAPERS_DIR,
            self.EMBEDDINGS_DIR,
            self.REPORTS_DIR,
        ]:
            d.mkdir(parents=True, exist_ok=True)


# Singleton instance used throughout the application
settings = Settings()
settings.ensure_dirs()
