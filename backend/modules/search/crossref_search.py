"""
ResearchAI — Module 2c: CrossRef Search
Queries the CrossRef REST API for DOI-registered scholarly works.
"""

from __future__ import annotations
from typing import List
import httpx

from researchai.backend.core.models import Paper, Author
from researchai.backend.core.exceptions import SearchError
from researchai.backend.core.logger import get_logger
from researchai.config import settings

logger = get_logger("crossref_search")


class CrossRefSearch:
    """Search CrossRef metadata for DOI-registered scholarly works."""

    BASE_URL = settings.CROSSREF_BASE_URL

    def search(self, query: str, max_results: int = 10,
               year_from: int = None, year_to: int = None) -> List[Paper]:
        logger.info("CrossRef search: '%s' (max=%d)", query, max_results)
        params: dict = {
            "query": query,
            "rows": min(max_results, 50),
            "select": "DOI,title,author,published,abstract,is-referenced-by-count,container-title,URL",
            "sort": "relevance",
        }
        if year_from:
            params["filter"] = f"from-pub-date:{year_from}"
        if year_to:
            f_val = params.get("filter", "")
            params["filter"] = f"{f_val},until-pub-date:{year_to}".lstrip(",")

        try:
            with httpx.Client(timeout=settings.REQUEST_TIMEOUT) as client:
                resp = client.get(self.BASE_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            raise SearchError(f"CrossRef request failed: {exc}") from exc

        papers: List[Paper] = []
        for item in data.get("message", {}).get("items", []):
            doi = item.get("DOI", "")
            titles = item.get("title", [])
            title = titles[0] if titles else ""

            raw_authors = item.get("author", [])
            authors = [
                Author(name=f"{a.get('given', '')} {a.get('family', '')}".strip())
                for a in raw_authors
            ]

            # Published year
            pub = item.get("published") or item.get("published-print") or {}
            date_parts = pub.get("date-parts", [[]])
            year = date_parts[0][0] if date_parts and date_parts[0] else None

            abstract = item.get("abstract", "")
            # CrossRef abstracts sometimes contain JATS XML tags
            if abstract:
                import re
                abstract = re.sub(r"<[^>]+>", "", abstract).strip()

            venue = ""
            ct = item.get("container-title", [])
            if ct:
                venue = ct[0]

            papers.append(Paper(
                id=f"doi:{doi}",
                title=title,
                authors=authors,
                abstract=abstract or None,
                year=year,
                source="crossref",
                doi=doi,
                url=item.get("URL", f"https://doi.org/{doi}"),
                citation_count=item.get("is-referenced-by-count"),
                venue=venue,
            ))

        logger.info("CrossRef returned %d results", len(papers))
        return papers
