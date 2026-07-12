"""
ResearchAI — Module 7: Multi-Paper Comparison
Generates structured comparison tables and narrative analyses
across multiple research papers.
"""

from __future__ import annotations
from typing import List, Optional, Dict
import uuid

from researchai.backend.core.models import (
    Paper, ExtractedPaper, ComparisonResult, PaperComparisonRow
)
from researchai.backend.core.watsonx_client import get_watsonx_client
from researchai.backend.core.logger import get_logger

logger = get_logger("comparison")

SYSTEM_PROMPT = """You are a research analyst specialising in comparative literature studies.
Compare papers objectively based only on their content. Be concise and use academic language."""


class PaperComparator:
    """
    Compares 2–10 research papers across key dimensions:
    methodology, dataset, accuracy, limitations, contributions.
    Returns both structured rows and a narrative summary.
    """

    def __init__(self) -> None:
        self.client = get_watsonx_client()

    def compare(
        self,
        papers: List[Paper],
        extracted: Dict[str, Optional[ExtractedPaper]],
        aspects: Optional[List[str]] = None,
    ) -> ComparisonResult:
        """Compare a list of papers and return structured results."""
        logger.info("Comparing %d papers", len(papers))
        if len(papers) < 2:
            raise ValueError("At least 2 papers are required for comparison.")

        rows: List[PaperComparisonRow] = []
        for p in papers:
            row = self._extract_row(p, extracted.get(p.id))
            rows.append(row)

        narrative = self._generate_narrative(papers, rows)
        differences = self._extract_differences(rows)
        common = self._extract_common(papers, rows)

        return ComparisonResult(
            papers=rows,
            narrative_comparison=narrative,
            key_differences=differences,
            common_ground=common,
            recommendation=self._recommend(rows, narrative),
        )

    def _extract_row(
        self, paper: Paper, extracted: Optional[ExtractedPaper]
    ) -> PaperComparisonRow:
        keys = ["method", "dataset", "accuracy", "metrics", "advantages",
                "limitations", "contribution"]
        source = ""
        if paper.abstract:
            source += f"Abstract: {paper.abstract}\n"
        if extracted:
            for s_name in ["methodology", "methods", "experiments", "results"]:
                if s_name in extracted.sections:
                    source += f"{s_name}: {extracted.sections[s_name][:1500]}\n"

        prompt = (
            f"Paper: '{paper.title}' ({paper.year})\n\n"
            f"{source[:4000]}\n\n"
            "Extract comparison data for this paper:"
        )
        structured = self.client.generate_structured(
            prompt=prompt,
            output_keys=keys,
            system_prompt=SYSTEM_PROMPT,
        )

        authors_str = ", ".join(
            a.get("name", "") if isinstance(a, dict) else getattr(a, "name", str(a))
            for a in paper.authors[:3]
        )
        return PaperComparisonRow(
            paper_id=paper.id,
            title=paper.title,
            year=paper.year,
            authors=authors_str,
            method=structured.get("method"),
            dataset=structured.get("dataset"),
            accuracy=structured.get("accuracy"),
            metrics=structured.get("metrics"),
            advantages=structured.get("advantages"),
            limitations=structured.get("limitations"),
            contribution=structured.get("contribution"),
        )

    def _generate_narrative(
        self, papers: List[Paper], rows: List[PaperComparisonRow]
    ) -> str:
        rows_text = "\n".join(
            f"- {r.title} ({r.year}): Method={r.method}, "
            f"Dataset={r.dataset}, Results={r.accuracy}"
            for r in rows
        )
        prompt = (
            f"Compare these {len(papers)} research papers:\n{rows_text}\n\n"
            "Write a 3-4 paragraph academic comparison covering: "
            "methodological approaches, datasets used, performance differences, "
            "and which paper advances the field most. Cite papers by title."
        )
        return self.client.generate(prompt, system_prompt=SYSTEM_PROMPT, max_new_tokens=768)

    def _extract_differences(self, rows: List[PaperComparisonRow]) -> List[str]:
        methods = [r.method for r in rows if r.method]
        datasets = [r.dataset for r in rows if r.dataset]
        diffs = []
        if len(set(methods)) > 1:
            diffs.append(f"Different methods: {' vs '.join(set(str(m)[:40] for m in methods))}")
        if len(set(datasets)) > 1:
            diffs.append(f"Different datasets: {' vs '.join(set(str(d)[:40] for d in datasets))}")
        if not diffs:
            diffs.append("Papers use similar approaches — see narrative for subtle differences.")
        return diffs

    def _extract_common(
        self, papers: List[Paper], rows: List[PaperComparisonRow]
    ) -> List[str]:
        common = []
        years = [r.year for r in rows if r.year]
        if years:
            common.append(f"All papers published between {min(years)}–{max(years)}")
        return common

    def _recommend(self, rows: List[PaperComparisonRow], narrative: str) -> str:
        titles = [r.title for r in rows[:3]]
        prompt = (
            f"Given these papers: {', '.join(titles)}, "
            f"and this analysis: {narrative[:500]}, "
            "which paper is most impactful and why? One sentence."
        )
        return self.client.generate(prompt, system_prompt=SYSTEM_PROMPT, max_new_tokens=150)
