"""
ResearchAI — Module 6: Paper Summarization
Generates structured, multi-level summaries of research papers.
"""

from __future__ import annotations
from typing import Optional
import uuid

from researchai.backend.core.models import PaperSummary, ExtractedPaper, Paper
from researchai.backend.core.watsonx_client import get_watsonx_client
from researchai.backend.core.logger import get_logger

logger = get_logger("summarizer")

SYSTEM_PROMPT = """You are an expert research paper analyst.
Produce accurate, structured summaries grounded only in the provided paper text.
Do not add information not present in the source. Be precise and academic."""


class PaperSummarizer:
    """
    Generates structured summaries at short, medium, or detailed level.
    Each summary includes: Problem, Objective, Methodology, Dataset,
    Algorithms, Results, Contributions, Limitations, and Future Work.
    """

    def __init__(self) -> None:
        self.client = get_watsonx_client()

    def summarize(
        self,
        paper: Paper,
        extracted: Optional[ExtractedPaper],
        level: str = "medium",
    ) -> PaperSummary:
        """Generate a structured paper summary at the requested level."""
        logger.info("Summarising paper: %s | level=%s", paper.id, level)

        source_text = self._build_source_text(paper, extracted)

        if level == "short":
            return self._short_summary(paper, source_text)
        elif level == "detailed":
            return self._detailed_summary(paper, source_text)
        else:
            return self._medium_summary(paper, source_text)

    # ------------------------------------------------------------------
    def _short_summary(self, paper: Paper, text: str) -> PaperSummary:
        prompt = (
            f"Paper Title: {paper.title}\n\n"
            f"Content:\n{text[:3000]}\n\n"
            "Write a concise 3-sentence summary of this paper covering: "
            "what problem it solves, how it solves it, and the main result."
        )
        answer = self.client.generate(prompt, system_prompt=SYSTEM_PROMPT, max_new_tokens=256)
        return PaperSummary(
            paper_id=paper.id,
            title=paper.title,
            summary_level="short",
            short_summary=answer,
            confidence=0.85,
        )

    def _medium_summary(self, paper: Paper, text: str) -> PaperSummary:
        keys = ["problem_statement", "methodology", "results", "contributions", "limitations"]
        prompt = (
            f"Paper Title: {paper.title}\n\n"
            f"Content:\n{text[:6000]}\n\n"
            "Summarise the following aspects of the paper:"
        )
        structured = self.client.generate_structured(
            prompt=prompt,
            output_keys=keys,
            system_prompt=SYSTEM_PROMPT,
        )
        return PaperSummary(
            paper_id=paper.id,
            title=paper.title,
            summary_level="medium",
            problem_statement=structured.get("problem_statement"),
            methodology=structured.get("methodology"),
            results=structured.get("results"),
            contributions=structured.get("contributions"),
            limitations=structured.get("limitations"),
            confidence=0.8,
            sources_used=[paper.id],
        )

    def _detailed_summary(self, paper: Paper, text: str) -> PaperSummary:
        keys = [
            "problem_statement", "objective", "methodology", "dataset",
            "algorithms", "results", "contributions", "limitations", "future_work"
        ]
        prompt = (
            f"Paper Title: {paper.title}\n\n"
            f"Content:\n{text[:10000]}\n\n"
            "Provide a comprehensive structured analysis of this research paper:"
        )
        structured = self.client.generate_structured(
            prompt=prompt,
            output_keys=keys,
            system_prompt=SYSTEM_PROMPT,
        )
        return PaperSummary(
            paper_id=paper.id,
            title=paper.title,
            summary_level="detailed",
            problem_statement=structured.get("problem_statement"),
            objective=structured.get("objective"),
            methodology=structured.get("methodology"),
            dataset=structured.get("dataset"),
            algorithms=structured.get("algorithms"),
            results=structured.get("results"),
            contributions=structured.get("contributions"),
            limitations=structured.get("limitations"),
            future_work=structured.get("future_work"),
            confidence=0.8,
            sources_used=[paper.id],
        )

    def _build_source_text(self, paper: Paper, extracted: Optional[ExtractedPaper]) -> str:
        parts = []
        if paper.abstract:
            parts.append(f"Abstract: {paper.abstract}")
        if extracted:
            if extracted.abstract:
                parts.append(f"Abstract: {extracted.abstract}")
            for section_name, section_text in extracted.sections.items():
                parts.append(f"\n--- {section_name.title()} ---\n{section_text[:2000]}")
        elif not parts:
            parts.append(paper.abstract or "No content available.")
        return "\n\n".join(parts)
