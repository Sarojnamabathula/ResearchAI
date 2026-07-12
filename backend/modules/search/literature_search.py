"""
ResearchAI — Module 2: Intelligent Literature Search
Aggregates results from arXiv, Semantic Scholar, and CrossRef.
All sources are queried concurrently and results are ranked by relevance.
"""

from __future__ import annotations
import asyncio
import hashlib
import time
from typing import List, Optional, Dict, Any
import httpx

from researchai.backend.core.models import Paper, Author, SearchQuery, SearchResult
from researchai.backend.core.logger import get_logger
from researchai.backend.core.exceptions import SearchError
from researchai.backend.modules.search.query_analyzer import QueryAnalyzer
from researchai.config import settings

logger = get_logger("literature_search")


# ---------------------------------------------------------------------------
# Source Adapters
# ---------------------------------------------------------------------------

class ArxivSearcher:
    """Search the arXiv preprint server via its Atom API."""

    BASE_URL = settings.ARXIV_BASE_URL

    async def search(self, query: str, max_results: int = 10) -> List[Paper]:
        import xml.etree.ElementTree as ET

        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance",
        }
        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
                resp = await client.get(self.BASE_URL, params=params)
                resp.raise_for_status()
        except Exception as exc:
            logger.warning("arXiv search error: %s", exc)
            return []

        papers: List[Paper] = []
        try:
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            root = ET.fromstring(resp.text)
            for entry in root.findall("atom:entry", ns):
                arxiv_id = (entry.findtext("atom:id", default="", namespaces=ns) or "").split("/")[-1]
                title = (entry.findtext("atom:title", default="", namespaces=ns) or "").replace("\n", " ").strip()
                abstract = (entry.findtext("atom:summary", default="", namespaces=ns) or "").replace("\n", " ").strip()
                published = entry.findtext("atom:published", default="", namespaces=ns) or ""
                year = int(published[:4]) if published else None
                authors = [
                    Author(name=a.findtext("atom:name", default="", namespaces=ns) or "")
                    for a in entry.findall("atom:author", ns)
                ]
                pdf_url = None
                url = f"https://arxiv.org/abs/{arxiv_id}"
                for link in entry.findall("atom:link", ns):
                    if link.get("type") == "application/pdf":
                        pdf_url = link.get("href")

                papers.append(Paper(
                    id=f"arxiv:{arxiv_id}",
                    title=title,
                    authors=authors,
                    abstract=abstract,
                    year=year,
                    source="arxiv",
                    url=url,
                    pdf_url=pdf_url or f"https://arxiv.org/pdf/{arxiv_id}",
                ))
        except Exception as exc:
            logger.error("arXiv parse error: %s", exc)
        logger.info("arXiv returned %d papers for '%s'", len(papers), query[:50])
        return papers


class SemanticScholarSearcher:
    """Search Semantic Scholar via its open Graph API."""

    BASE_URL = settings.SEMANTIC_SCHOLAR_BASE_URL

    async def search(self, query: str, max_results: int = 10) -> List[Paper]:
        fields = "paperId,title,authors,year,abstract,citationCount,externalIds,venue,openAccessPdf"
        headers = {}
        if settings.SEMANTIC_SCHOLAR_API_KEY:
            headers["x-api-key"] = settings.SEMANTIC_SCHOLAR_API_KEY
        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/paper/search",
                    params={"query": query, "limit": max_results, "fields": fields},
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning("Semantic Scholar search error: %s", exc)
            return []

        papers: List[Paper] = []
        for item in data.get("data", []):
            try:
                doi = (item.get("externalIds") or {}).get("DOI")
                pdf_info = item.get("openAccessPdf") or {}
                papers.append(Paper(
                    id=f"ss:{item['paperId']}",
                    title=item.get("title", ""),
                    authors=[Author(name=a.get("name", "")) for a in item.get("authors", [])],
                    abstract=item.get("abstract"),
                    year=item.get("year"),
                    source="semantic_scholar",
                    doi=doi,
                    url=f"https://www.semanticscholar.org/paper/{item['paperId']}",
                    pdf_url=pdf_info.get("url"),
                    citation_count=item.get("citationCount"),
                    venue=item.get("venue"),
                ))
            except Exception:
                continue
        logger.info("Semantic Scholar returned %d papers for '%s'", len(papers), query[:50])
        return papers


class CrossRefSearcher:
    """Search CrossRef for DOI-registered academic work."""

    BASE_URL = settings.CROSSREF_BASE_URL

    async def search(self, query: str, max_results: int = 10) -> List[Paper]:
        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
                resp = await client.get(
                    self.BASE_URL,
                    params={
                        "query": query,
                        "rows": max_results,
                        "select": "DOI,title,author,published,abstract,is-referenced-by-count,container-title",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning("CrossRef search error: %s", exc)
            return []

        papers: List[Paper] = []
        for item in data.get("message", {}).get("items", []):
            try:
                titles = item.get("title", [])
                title = titles[0] if titles else ""
                doi = item.get("DOI", "")
                year = None
                pub_date = item.get("published", {}).get("date-parts", [[]])
                if pub_date and pub_date[0]:
                    year = pub_date[0][0]
                authors = []
                for a in item.get("author", []):
                    name = f"{a.get('given', '')} {a.get('family', '')}".strip()
                    authors.append(Author(name=name))
                venue_list = item.get("container-title", [])
                venue = venue_list[0] if venue_list else None
                papers.append(Paper(
                    id=f"crossref:{hashlib.md5(doi.encode()).hexdigest()[:12]}",
                    title=title,
                    authors=authors,
                    abstract=item.get("abstract", ""),
                    year=year,
                    source="crossref",
                    doi=doi,
                    url=f"https://doi.org/{doi}" if doi else None,
                    citation_count=item.get("is-referenced-by-count"),
                    venue=venue,
                ))
            except Exception:
                continue
        logger.info("CrossRef returned %d papers for '%s'", len(papers), query[:50])
        return papers


# ---------------------------------------------------------------------------
# Unified Search Service
# ---------------------------------------------------------------------------

class LiteratureSearchService:
    """
    Orchestrates parallel search across all configured sources,
    deduplicates results, and ranks by relevance score.
    """

    def __init__(self) -> None:
        self.arxiv = ArxivSearcher()
        self.semantic_scholar = SemanticScholarSearcher()
        self.crossref = CrossRefSearcher()
        self.analyzer = QueryAnalyzer()
        self._source_map = {
            "arxiv": self.arxiv.search,
            "semantic_scholar": self.semantic_scholar.search,
            "crossref": self.crossref.search,
        }

    async def search(self, query: SearchQuery) -> SearchResult:
        """Execute a research query against all specified sources."""
        start = time.time()

        # Analyse query for metadata
        analysis = self.analyzer.analyze(query.query)
        expanded_query = analysis.topic or query.query

        logger.info(
            "Literature search | topic='%s' | sources=%s | max=%d",
            expanded_query, query.sources, query.max_results,
        )

        # Concurrent search across all sources
        tasks = [
            self._source_map[src](expanded_query, query.max_results)
            for src in query.sources
            if src in self._source_map
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_papers: List[Paper] = []
        for src, result in zip(query.sources, results):
            if isinstance(result, Exception):
                logger.warning("Source %s failed: %s", src, result)
            else:
                all_papers.extend(result)

        # Deduplicate by title similarity
        unique_papers = self._deduplicate(all_papers)

        # Apply year filter
        if query.year_from or query.year_to:
            unique_papers = [
                p for p in unique_papers
                if p.year and
                (not query.year_from or p.year >= query.year_from) and
                (not query.year_to or p.year <= query.year_to)
            ]

        # Rank
        ranked = self._rank(unique_papers, query.query, query.sort_by)
        elapsed = (time.time() - start) * 1000

        return SearchResult(
            query=query.query,
            papers=ranked[:query.max_results],
            total_found=len(ranked),
            sources_queried=query.sources,
            search_time_ms=round(elapsed, 1),
            keywords_extracted=analysis.keywords,
            related_concepts=analysis.related_concepts,
        )

    # ------------------------------------------------------------------
    def _deduplicate(self, papers: List[Paper]) -> List[Paper]:
        seen_titles: set = set()
        unique: List[Paper] = []
        for p in papers:
            key = p.title.lower().strip()[:60]
            if key not in seen_titles:
                seen_titles.add(key)
                unique.append(p)
        return unique

    def _rank(self, papers: List[Paper], query: str, sort_by: str) -> List[Paper]:
        if sort_by == "date":
            return sorted(papers, key=lambda p: p.year or 0, reverse=True)
        if sort_by == "citations":
            return sorted(papers, key=lambda p: p.citation_count or 0, reverse=True)
        # Default: relevance — naive keyword overlap score
        qwords = set(query.lower().split())
        for p in papers:
            title_words = set((p.title or "").lower().split())
            abstract_words = set((p.abstract or "")[:500].lower().split())
            score = len(qwords & title_words) * 2 + len(qwords & abstract_words)
            p.relevance_score = float(score)
        return sorted(papers, key=lambda p: p.relevance_score or 0, reverse=True)
