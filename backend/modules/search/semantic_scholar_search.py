"""
ResearchAI — Module 2b: Semantic Scholar Search
Queries the Semantic Scholar Graph API for papers, abstracts, and citations.
"""

from __future__ import annotations
from typing import List, Optional
import httpx

from researchai.backend.core.models import Paper, Author
from researchai.backend.core.exceptions import SearchError
from researchai.backend.core.logger import get_logger
from researchai.config import settings

logger = get_logger("semantic_scholar")

FIELDS = "paperId,title,authors,year,abstract,citationCount,externalIds,venue,openAccessPdf"


class SemanticScholarSearch:
    """Search Semantic Scholar via the public Graph API."""

    BASE_URL = settings.SEMANTIC_SCHOLAR_BASE_URL

    def __init__(self) -> None:
        self._headers = {}
        if settings.SEMANTIC_SCHOLAR_API_KEY:
            self._headers["x-api-key"] = settings.SEMANTIC_SCHOLAR_API_KEY

    def search(self, query: str, max_results: int = 10,
               year_from: int = None, year_to: int = None) -> List[Paper]:
        logger.info("Semantic Scholar search: '%s' (max=%d)", query, max_results)
        params: dict = {
            "query": query,
            "limit": min(max_results, 100),
            "fields": FIELDS,
        }
        if year_from or year_to:
            y1 = year_from or ""
            y2 = year_to or ""
            params["year"] = f"{y1}-{y2}"

        try:
            with httpx.Client(timeout=settings.REQUEST_TIMEOUT,
                              headers=self._headers) as client:
                resp = client.get(f"{self.BASE_URL}/paper/search", params=params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            raise SearchError(f"Semantic Scholar request failed: {exc}") from exc

        papers: List[Paper] = []
        for item in data.get("data", []):
            pid = item.get("paperId", "")
            ext = item.get("externalIds") or {}
            doi = ext.get("DOI")
            arxiv_id = ext.get("ArXiv")

            authors = [
                Author(name=a.get("name", ""))
                for a in item.get("authors", [])
            ]

            oa = item.get("openAccessPdf") or {}
            pdf_url = oa.get("url")

            papers.append(Paper(
                id=f"s2:{pid}",
                title=item.get("title", ""),
                authors=authors,
                abstract=item.get("abstract"),
                year=item.get("year"),
                source="semantic_scholar",
                doi=doi,
                url=f"https://www.semanticscholar.org/paper/{pid}",
                pdf_url=pdf_url or (f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else None),
                citation_count=item.get("citationCount"),
                venue=item.get("venue"),
            ))

        logger.info("Semantic Scholar returned %d results", len(papers))
        return papers
