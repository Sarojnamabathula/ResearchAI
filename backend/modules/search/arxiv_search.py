"""
ResearchAI — Module 2a: arXiv Search
Queries the arXiv API and returns normalised Paper objects.
"""

from __future__ import annotations
import xml.etree.ElementTree as ET
from typing import List
import httpx

from researchai.backend.core.models import Paper, Author
from researchai.backend.core.exceptions import SearchError
from researchai.backend.core.logger import get_logger
from researchai.config import settings

logger = get_logger("arxiv_search")

NS = "http://www.w3.org/2005/Atom"
ARXIV_NS = "http://arxiv.org/schemas/atom"


class ArxivSearch:
    """Search the arXiv open-access repository."""

    BASE_URL = settings.ARXIV_BASE_URL

    def search(self, query: str, max_results: int = 10,
               year_from: int = None, year_to: int = None) -> List[Paper]:
        logger.info("arXiv search: '%s' (max=%d)", query, max_results)
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": min(max_results, 50),
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
        try:
            with httpx.Client(timeout=settings.REQUEST_TIMEOUT) as client:
                resp = client.get(self.BASE_URL, params=params)
                resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise SearchError(f"arXiv request failed: {exc}") from exc

        return self._parse(resp.text, year_from, year_to)

    def _parse(self, xml_text: str,
               year_from: int = None, year_to: int = None) -> List[Paper]:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            raise SearchError(f"arXiv XML parse error: {exc}") from exc

        papers: List[Paper] = []
        for entry in root.findall(f"{{{NS}}}entry"):
            raw_id = (entry.findtext(f"{{{NS}}}id") or "").strip()
            arxiv_id = raw_id.split("/abs/")[-1].split("v")[0]

            title = (entry.findtext(f"{{{NS}}}title") or "").replace("\n", " ").strip()
            abstract = (entry.findtext(f"{{{NS}}}summary") or "").replace("\n", " ").strip()
            published = (entry.findtext(f"{{{NS}}}published") or "")[:4]
            year = int(published) if published.isdigit() else None

            if year_from and year and year < year_from:
                continue
            if year_to and year and year > year_to:
                continue

            authors = []
            for a in entry.findall(f"{{{NS}}}author"):
                name = a.findtext(f"{{{NS}}}name") or ""
                if name:
                    authors.append(Author(name=name))

            pdf_url = None
            for link in entry.findall(f"{{{NS}}}link"):
                if link.attrib.get("type") == "application/pdf":
                    pdf_url = link.attrib.get("href")

            papers.append(Paper(
                id=f"arxiv:{arxiv_id}",
                title=title,
                authors=authors,
                abstract=abstract,
                year=year,
                source="arxiv",
                doi=f"10.48550/arXiv.{arxiv_id}",
                url=f"https://arxiv.org/abs/{arxiv_id}",
                pdf_url=pdf_url or f"https://arxiv.org/pdf/{arxiv_id}.pdf",
            ))

        logger.info("arXiv returned %d results", len(papers))
        return papers
