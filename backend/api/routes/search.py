"""
Search API Routes
POST /api/search       — multi-source literature search
GET  /api/search/analyze — query analysis only
GET  /api/search/history — search history
"""

from fastapi import APIRouter
from researchai.backend.core.models import SearchQuery, SearchResult, QueryAnalysis
from researchai.backend.modules.search.search_engine import SearchEngine
from researchai.backend.modules.search.query_analyzer import QueryAnalyzer
from researchai.backend.db.database import get_search_history

router = APIRouter()
_engine = SearchEngine()
_analyzer = QueryAnalyzer()


@router.post("", response_model=SearchResult)
async def search_papers(query: SearchQuery) -> SearchResult:
    """
    Search academic literature across arXiv, Semantic Scholar, and CrossRef.
    Results are deduplicated, ranked by relevance, and persisted to the database.
    """
    return await _engine.search(query)


@router.get("/analyze", response_model=QueryAnalysis)
async def analyze_query(q: str) -> QueryAnalysis:
    """
    Analyse a research query using IBM Granite to extract keywords,
    domain, intent, and search expansions.
    """
    return _analyzer.analyze(q)


@router.get("/history")
async def search_history(limit: int = 20):
    """Return recent search history from the database."""
    return await get_search_history(limit=limit)
