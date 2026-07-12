"""
ResearchAI — Module 8: Literature Review Generator
Produces coherent academic literature reviews from a collection of papers.
"""

from __future__ import annotations
from typing import List, Dict, Optional
import uuid

from researchai.backend.core.models import Paper, ExtractedPaper, LiteratureReview
from researchai.backend.core.watsonx_client import get_watsonx_client
from researchai.backend.core.logger import get_logger

logger = get_logger("literature_review")

SYSTEM_PROMPT = """You are an expert academic writer with deep knowledge of writing 
structured literature reviews for top-tier research venues. 
Write in a formal, coherent, and analytical academic tone.
Only use information present in the provided papers."""


class LiteratureReviewGenerator:
    """
    Automatically generates a complete literature review from a list of papers.
    Groups related works, identifies trends, discusses strengths/weaknesses.
    """

    def __init__(self) -> None:
        self.client = get_watsonx_client()

    def generate(
        self,
        topic: str,
        papers: List[Paper],
        extracted: Dict[str, Optional[ExtractedPaper]],
    ) -> LiteratureReview:
        logger.info("Generating literature review | topic='%s' | %d papers", topic, len(papers))

        paper_summaries = self._build_paper_summaries(papers, extracted)

        abstract = self._generate_section(
            "Write a 150-word abstract for a literature review on the topic of "
            f"'{topic}' covering {len(papers)} papers.",
            paper_summaries,
        )

        introduction = self._generate_section(
            f"Write a 300-word introduction for a literature review on '{topic}'. "
            "Explain the importance of this research area and the scope of this review.",
            paper_summaries,
        )

        thematic_sections = self._generate_thematic_sections(topic, papers, paper_summaries)

        trends_raw = self.client.generate(
            f"Based on these papers on '{topic}':\n{paper_summaries[:3000]}\n\n"
            "List 5-7 key research trends, one per line.",
            system_prompt=SYSTEM_PROMPT,
            max_new_tokens=300,
        )
        trends = [t.strip("- •") for t in trends_raw.splitlines() if t.strip()][:7]

        gaps_raw = self.client.generate(
            f"Based on these papers on '{topic}':\n{paper_summaries[:3000]}\n\n"
            "List 5 major unresolved challenges or research weaknesses, one per line.",
            system_prompt=SYSTEM_PROMPT,
            max_new_tokens=300,
        )
        unresolved = [g.strip("- •") for g in gaps_raw.splitlines() if g.strip()][:5]

        conclusion = self._generate_section(
            f"Write a 200-word conclusion summarising the literature review on '{topic}'. "
            "Discuss the overall state of research and future directions.",
            paper_summaries,
        )

        references = self._build_references(papers)

        return LiteratureReview(
            topic=topic,
            abstract=abstract,
            introduction=introduction,
            thematic_sections=thematic_sections,
            trends=trends,
            weaknesses=unresolved,
            conclusion=conclusion,
            references=references,
            paper_count=len(papers),
        )

    # ------------------------------------------------------------------
    def _build_paper_summaries(
        self, papers: List[Paper], extracted: Dict[str, Optional[ExtractedPaper]]
    ) -> str:
        parts = []
        for p in papers:
            ext = extracted.get(p.id)
            abstract = (ext.abstract if ext and ext.abstract else p.abstract) or ""
            parts.append(
                f"[{p.id}] \"{p.title}\" ({p.year})\n"
                f"Authors: {', '.join(getattr(a, 'name', str(a)) for a in p.authors[:3])}\n"
                f"Abstract: {abstract[:400]}"
            )
        return "\n\n".join(parts)

    def _generate_section(self, instruction: str, context: str) -> str:
        prompt = f"{instruction}\n\nPapers:\n{context[:5000]}"
        return self.client.generate(prompt, system_prompt=SYSTEM_PROMPT, max_new_tokens=512)

    def _generate_thematic_sections(
        self, topic: str, papers: List[Paper], summaries: str
    ) -> Dict[str, str]:
        themes_raw = self.client.generate(
            f"For a literature review on '{topic}', identify 3-5 thematic groups "
            f"that best organise these {len(papers)} papers. List only theme names, one per line.\n\n"
            f"{summaries[:2000]}",
            system_prompt=SYSTEM_PROMPT,
            max_new_tokens=200,
        )
        themes = [t.strip("- •123456789.") for t in themes_raw.splitlines() if t.strip()][:5]
        if not themes:
            themes = ["Methods and Approaches", "Datasets and Evaluation", "Results and Findings"]

        sections: Dict[str, str] = {}
        for theme in themes:
            content = self.client.generate(
                f"Write a 200-word paragraph for the thematic section '{theme}' "
                f"in a literature review on '{topic}'. Reference specific papers from:\n{summaries[:3000]}",
                system_prompt=SYSTEM_PROMPT,
                max_new_tokens=400,
            )
            sections[theme] = content
        return sections

    def _build_references(self, papers: List[Paper]) -> List[str]:
        refs = []
        for p in papers:
            authors = ", ".join(getattr(a, "name", str(a)) for a in p.authors[:3])
            year = p.year or "n.d."
            url = p.url or p.doi or ""
            refs.append(f"{authors} ({year}). {p.title}. {url}")
        return refs
