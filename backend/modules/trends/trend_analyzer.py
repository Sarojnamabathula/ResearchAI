"""
ResearchAI — Module 15: Trend Analysis
Analyses publication trends, keyword frequency, emerging topics,
most active authors, and research growth from a paper collection.
"""

from __future__ import annotations
from collections import Counter
from typing import List, Dict, Any

from researchai.backend.core.models import Paper, TrendAnalysis, TrendData
from researchai.backend.core.watsonx_client import get_watsonx_client
from researchai.backend.core.logger import get_logger

logger = get_logger("trend_analysis")

SYSTEM_PROMPT = """You are a bibliometric analyst specialising in research trend analysis.
Provide accurate, data-driven insights about research trajectories."""


class TrendAnalyzer:
    """
    Analyses a collection of papers to extract publication trends,
    keyword frequency, emerging topics, and active contributors.
    """

    def __init__(self) -> None:
        self.client = get_watsonx_client()

    def analyze(self, topic: str, papers: List[Paper]) -> TrendAnalysis:
        logger.info("Trend analysis | topic='%s' | %d papers", topic, len(papers))

        # Publication trends per year
        pub_trends = self._publication_trends(papers)

        # Top keywords (from titles + abstracts)
        top_keywords = self._extract_keywords(papers)

        # Most cited authors
        top_authors = self._top_authors(papers)

        # Most active venues
        top_venues = self._top_venues(papers)

        # Growth rate
        growth = self._compute_growth(papers)

        # Emerging topics via AI
        emerging = self._emerging_topics(topic, papers)

        return TrendAnalysis(
            topic=topic,
            publication_trends=[pub_trends],
            top_keywords=top_keywords,
            emerging_topics=emerging,
            most_active_authors=top_authors,
            most_active_venues=top_venues,
            growth_rate=growth,
        )

    # ------------------------------------------------------------------
    def _publication_trends(self, papers: List[Paper]) -> TrendData:
        year_counter: Counter = Counter()
        for p in papers:
            if p.year:
                year_counter[p.year] += 1
        years = sorted(year_counter.keys())
        values = [year_counter[y] for y in years]
        return TrendData(label="Publications per Year", years=years, values=values)

    def _extract_keywords(self, papers: List[Paper]) -> List[Dict[str, Any]]:
        import re
        # Simple frequency-based keyword extraction from titles
        stop_words = {
            "a", "an", "the", "in", "of", "for", "and", "with", "on",
            "to", "is", "are", "using", "based", "learning", "deep",
            "via", "by", "from", "our", "we", "paper", "study",
        }
        word_counter: Counter = Counter()
        for p in papers:
            words = re.findall(r"\b[a-z]{4,}\b", (p.title or "").lower())
            for word in words:
                if word not in stop_words:
                    word_counter[word] += 1
        return [
            {"keyword": kw, "count": cnt}
            for kw, cnt in word_counter.most_common(20)
        ]

    def _top_authors(self, papers: List[Paper]) -> List[Dict[str, Any]]:
        author_counter: Counter = Counter()
        for p in papers:
            for a in p.authors:
                name = a.name if hasattr(a, "name") else a.get("name", "")
                if name:
                    author_counter[name] += 1
        return [
            {"author": name, "papers": cnt}
            for name, cnt in author_counter.most_common(10)
        ]

    def _top_venues(self, papers: List[Paper]) -> List[Dict[str, Any]]:
        venue_counter: Counter = Counter()
        for p in papers:
            if p.venue:
                venue_counter[p.venue] += 1
        return [
            {"venue": v, "count": c}
            for v, c in venue_counter.most_common(10)
        ]

    def _compute_growth(self, papers: List[Paper]) -> float:
        """Year-over-year growth rate of publications."""
        year_counter: Counter = Counter()
        for p in papers:
            if p.year:
                year_counter[p.year] += 1
        years = sorted(year_counter.keys())
        if len(years) < 2:
            return 0.0
        first_year = year_counter[years[0]]
        last_year = year_counter[years[-1]]
        if first_year == 0:
            return 0.0
        n_years = years[-1] - years[0]
        if n_years == 0:
            return 0.0
        cagr = ((last_year / first_year) ** (1 / n_years)) - 1
        return round(cagr * 100, 2)

    def _emerging_topics(self, topic: str, papers: List[Paper]) -> List[str]:
        titles = [p.title for p in papers[-10:] if p.title]  # most recent
        prompt = (
            f"Based on these recent papers on '{topic}':\n"
            + "\n".join(f"- {t}" for t in titles)
            + "\n\nList 5 emerging sub-topics or trends in this field, one per line."
        )
        raw = self.client.generate(prompt, system_prompt=SYSTEM_PROMPT, max_new_tokens=250)
        return [l.strip("- •123456789.") for l in raw.splitlines() if l.strip()][:5]
