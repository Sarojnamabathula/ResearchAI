"""
ResearchAI — Module 2: Intelligent Literature Search Engine
Orchestrates multi-source search, deduplicates results,
ranks by relevance, and persists to the database.
"""

from __future__ import annotations
import asyncio
import time
import hashlib
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict

from researchai.backend.core.models import Paper, SearchQuery, SearchResult
from researchai.backend.core.logger import get_logger
from researchai.backend.db.database import save_paper, log_search
from researchai.backend.modules.search.arxiv_search import ArxivSearch
from researchai.backend.modules.search.semantic_scholar_search import SemanticScholarSearch
from researchai.backend.modules.search.crossref_search import CrossRefSearch
from researchai.backend.modules.search.query_analyzer import QueryAnalyzer

logger = get_logger("search_engine")

# Shared thread pool for running sync HTTP search clients concurrently
_executor = ThreadPoolExecutor(max_workers=6)


class SearchEngine:
    """
    Unified multi-source academic search engine.
    Aggregates results from arXiv, Semantic Scholar, and CrossRef,
    deduplicates by title, and ranks by citation count + recency.
    All three sources are queried in parallel using an asyncio thread pool.
    """

    def __init__(self) -> None:
        self._arxiv = ArxivSearch()
        self._s2 = SemanticScholarSearch()
        self._crossref = CrossRefSearch()
        self._analyzer = QueryAnalyzer()

    async def search(self, query: SearchQuery) -> SearchResult:
        """Execute a full multi-source search and return ranked results."""
        t0 = time.time()
        analysis = self._analyzer.analyze(query.query)

        # Use AI-extracted keywords as the actual search string when useful
        search_string = query.query
        if analysis.keywords:
            search_string = " ".join(analysis.keywords[:5])

        source_map = {
            "arxiv": self._arxiv,
            "semantic_scholar": self._s2,
            "crossref": self._crossref,
        }

        per_source = max(query.max_results, 10)

        # Build tasks only for requested, known sources
        valid_sources = [s for s in query.sources if s in source_map]
        unknown = [s for s in query.sources if s not in source_map]
        for s in unknown:
            logger.warning("Unknown source requested: %s", s)

        loop = asyncio.get_event_loop()

        async def _fetch(source_name: str) -> tuple[str, List[Paper]]:
            searcher = source_map[source_name]
            try:
                results = await loop.run_in_executor(
                    _executor,
                    lambda: searcher.search(
                        search_string,
                        max_results=per_source,
                        year_from=query.year_from,
                        year_to=query.year_to,
                    ),
                )
                return source_name, results
            except Exception as exc:
                logger.warning("Source %s failed: %s", source_name, exc)
                return source_name, []

        # Parallel fetch
        fetch_results = await asyncio.gather(*[_fetch(s) for s in valid_sources])

        all_papers: List[Paper] = []
        sources_queried: List[str] = []
        for source_name, papers in fetch_results:
            if papers:
                all_papers.extend(papers)
                sources_queried.append(source_name)

        # Deduplicate by normalised title
        unique = self._deduplicate(all_papers)

        # Rank
        ranked = self._rank(unique, query.query, query.sort_by)[:query.max_results]

        # Assign relevance scores
        for i, p in enumerate(ranked):
            p.relevance_score = round(1.0 - i / max(len(ranked), 1), 3)

        # Persist to DB (fire-and-forget per paper)
        for p in ranked:
            try:
                await save_paper(p.dict())
            except Exception as exc:
                logger.warning("Failed to persist paper %s: %s", p.id, exc)

        elapsed = round((time.time() - t0) * 1000, 1)

        # Log search
        try:
            await log_search(query.query, sources_queried, len(ranked))
        except Exception:
            pass

        logger.info(
            "Search complete | query='%s' | results=%d | time=%dms",
            query.query, len(ranked), elapsed,
        )

        return SearchResult(
            query=query.query,
            papers=ranked,
            total_found=len(ranked),
            sources_queried=sources_queried,
            search_time_ms=elapsed,
            keywords_extracted=analysis.keywords,
            related_concepts=analysis.related_concepts,
        )

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------

    @staticmethod
    def _deduplicate(papers: List[Paper]) -> List[Paper]:
        seen: Dict[str, Paper] = {}
        for p in papers:
            key = hashlib.md5(
                p.title.lower().strip().encode()
            ).hexdigest()
            if key not in seen:
                seen[key] = p
            else:
                # Prefer paper with more metadata
                existing = seen[key]
                if (p.citation_count or 0) > (existing.citation_count or 0):
                    seen[key] = p
        return list(seen.values())

    # ------------------------------------------------------------------
    # Ranking
    # ------------------------------------------------------------------

    @staticmethod
    def _rank(papers: List[Paper], query: str, sort_by: str) -> List[Paper]:
        query_lower = query.lower()

        def score(p: Paper) -> float:
            s = 0.0
            # Title match
            if query_lower in (p.title or "").lower():
                s += 10.0
            # Citation count (log-scaled)
            import math
            citations = p.citation_count or 0
            s += math.log1p(citations) * 0.5
            # Recency
            year = p.year or 2000
            s += (year - 2000) * 0.1
            return s

        if sort_by == "citations":
            return sorted(papers, key=lambda p: p.citation_count or 0, reverse=True)
        if sort_by == "date":
            return sorted(papers, key=lambda p: p.year or 0, reverse=True)
        return sorted(papers, key=score, reverse=True)
