"""
ResearchAI — Module 1: Research Question Understanding
Analyses a natural language query to extract topic, domain, keywords,
related concepts, and potential search expansions using IBM Granite.
"""

from __future__ import annotations
import re
from typing import List

from researchai.backend.core.models import QueryAnalysis
from researchai.backend.core.watsonx_client import get_watsonx_client
from researchai.backend.core.logger import get_logger

logger = get_logger("query_analyzer")

SYSTEM_PROMPT = """You are a research assistant specialised in academic literature analysis.
When given a user query, extract structured metadata to guide a literature search."""


class QueryAnalyzer:
    """
    Converts a free-text research question into a structured QueryAnalysis
    with topic, domain, keywords, intent, related concepts, and expansions.
    """

    def __init__(self) -> None:
        self.client = get_watsonx_client()

    def analyze(self, query: str) -> QueryAnalysis:
        """Analyse a research query and return structured metadata."""
        logger.info("Analysing query: %s", query[:80])

        prompt = f"""Analyse the following research query and extract information.

Query: "{query}"

Provide the following fields:
topic: (main research topic in 3-8 words)
domain: (academic domain, e.g., Computer Science, Medicine, Physics)
keywords: (comma-separated list of 5-10 search keywords)
related_concepts: (comma-separated list of 5 related concepts)
search_expansions: (comma-separated list of 3 alternative search phrasings)
intent: (one of: find_papers | summarize | compare | identify_gaps | literature_review | general_question)
"""

        structured = self.client.generate_structured(
            prompt=prompt,
            output_keys=["topic", "domain", "keywords", "related_concepts",
                         "search_expansions", "intent"],
            system_prompt=SYSTEM_PROMPT,
        )

        return QueryAnalysis(
            original_query=query,
            topic=structured.get("topic", query),
            domain=structured.get("domain", "Computer Science"),
            keywords=self._split_list(structured.get("keywords", query)),
            related_concepts=self._split_list(structured.get("related_concepts", "")),
            search_expansions=self._split_list(structured.get("search_expansions", "")),
            intent=structured.get("intent", "find_papers"),
        )

    # ------------------------------------------------------------------
    def _split_list(self, value: str) -> List[str]:
        """Split a comma-separated string into a cleaned list."""
        if not value:
            return []
        items = re.split(r"[,;|]+", value)
        return [i.strip() for i in items if i.strip()]
