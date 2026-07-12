"""
ResearchAI — Module 12: Report Generator
Generates comprehensive, export-ready research reports combining
all AI analysis modules into one coherent document.
"""

from __future__ import annotations
from typing import List, Dict, Optional

from researchai.backend.core.models import (
    Paper, ExtractedPaper, ReportRequest, ResearchReport
)
from researchai.backend.core.watsonx_client import get_watsonx_client
from researchai.backend.modules.literature_review.review_generator import LiteratureReviewGenerator
from researchai.backend.modules.comparison.comparator import PaperComparator
from researchai.backend.modules.gap_analysis.gap_analyzer import ResearchGapAnalyzer
from researchai.backend.modules.citation.citation_manager import CitationManager
from researchai.backend.core.logger import get_logger

logger = get_logger("report_generator")

SYSTEM_PROMPT = """You are an expert academic writer producing a high-quality research report.
Write in formal academic English. Be precise and evidence-based. 
Only reference information from provided paper content."""


class ReportGenerator:
    """
    Generates a complete academic research report by orchestrating
    the Literature Review, Comparison, Gap Analysis, and Citation modules.
    """

    def __init__(self) -> None:
        self.client = get_watsonx_client()
        self.review_gen = LiteratureReviewGenerator()
        self.comparator = PaperComparator()
        self.gap_analyzer = ResearchGapAnalyzer()
        self.citation_mgr = CitationManager()

    def generate(
        self,
        request: ReportRequest,
        papers: List[Paper],
        extracted: Dict[str, Optional[ExtractedPaper]],
    ) -> ResearchReport:
        logger.info(
            "Generating report | topic='%s' | papers=%d | fmt=%s",
            request.topic, len(papers), request.citation_format,
        )

        context = self._build_paper_context(papers, extracted)

        # --- Title ---
        title = request.topic if len(request.topic) > 10 else (
            f"A Survey of {request.topic}: State of the Art and Future Directions"
        )

        # --- Abstract ---
        abstract = self.client.generate(
            f"Write a 150-word abstract for a research report titled '{title}' "
            f"covering {len(papers)} papers.\n\nPapers:\n{context[:2000]}",
            system_prompt=SYSTEM_PROMPT,
            max_new_tokens=256,
        )

        # --- Introduction ---
        introduction = self.client.generate(
            f"Write a 400-word introduction for the report '{title}'. "
            "Motivate the topic, state objectives, and outline structure.\n\n"
            f"Papers:\n{context[:3000]}",
            system_prompt=SYSTEM_PROMPT,
            max_new_tokens=512,
        )

        # --- Background ---
        background = self.client.generate(
            f"Write a 350-word background section for '{title}'. "
            "Explain foundational concepts and terminology.\n\n"
            f"Papers:\n{context[:2500]}",
            system_prompt=SYSTEM_PROMPT,
            max_new_tokens=512,
        )

        # --- Literature Review ---
        lit_review_text = ""
        try:
            review = self.review_gen.generate(request.topic, papers, extracted)
            lit_review_text = (
                review.introduction + "\n\n" +
                "\n\n".join(
                    f"**{k}**\n{v}"
                    for k, v in review.thematic_sections.items()
                ) + "\n\n" + review.conclusion
            )
        except Exception as exc:
            logger.warning("Literature review generation failed: %s", exc)
            lit_review_text = self.client.generate(
                f"Write a 600-word literature review for '{request.topic}'.\n\n{context[:4000]}",
                system_prompt=SYSTEM_PROMPT,
                max_new_tokens=768,
            )

        # --- Comparative Analysis ---
        comparative = ""
        if len(papers) >= 2:
            try:
                comparison = self.comparator.compare(papers[:5], extracted)
                comparative = comparison.narrative_comparison
            except Exception as exc:
                logger.warning("Comparison failed: %s", exc)
                comparative = self.client.generate(
                    f"Compare the methodologies of these papers:\n{context[:3000]}",
                    system_prompt=SYSTEM_PROMPT,
                    max_new_tokens=512,
                )

        # --- Research Gap ---
        gap_text = ""
        try:
            gaps = self.gap_analyzer.analyze(request.topic, papers)
            if gaps.gaps:
                gap_items = "\n".join(
                    f"- **{g.title}**: {g.description}" for g in gaps.gaps
                )
                gap_text = f"{gaps.summary}\n\n{gap_items}"
            else:
                gap_text = gaps.summary
        except Exception as exc:
            logger.warning("Gap analysis failed: %s", exc)
            gap_text = self.client.generate(
                f"Identify research gaps in '{request.topic}'.\n\n{context[:2000]}",
                system_prompt=SYSTEM_PROMPT,
                max_new_tokens=400,
            )

        # --- Proposed Direction ---
        proposed = self.client.generate(
            f"Propose 3 concrete future research directions for '{request.topic}' "
            "based on identified gaps. Be specific and actionable.\n\n"
            f"Gaps summary: {gap_text[:1000]}",
            system_prompt=SYSTEM_PROMPT,
            max_new_tokens=400,
        )

        # --- References ---
        coll = self.citation_mgr.generate_collection(papers, request.citation_format)
        references = [c.citation_text for c in coll.citations]

        # Word count
        full_content = " ".join([abstract, introduction, background,
                                  lit_review_text, comparative, gap_text, proposed])
        word_count = len(full_content.split())

        return ResearchReport(
            title=title,
            abstract=abstract,
            introduction=introduction,
            background=background,
            literature_review=lit_review_text,
            comparative_analysis=comparative,
            research_gap=gap_text,
            proposed_direction=proposed,
            references=references,
            citation_format=request.citation_format,
            paper_count=len(papers),
            word_count=word_count,
        )

    def _build_paper_context(
        self, papers: List[Paper], extracted: Dict[str, Optional[ExtractedPaper]]
    ) -> str:
        parts = []
        for p in papers:
            ext = extracted.get(p.id)
            abstract = (ext.abstract if ext and ext.abstract else p.abstract) or ""
            parts.append(
                f"[{p.id}] \"{p.title}\" ({p.year})\n{abstract[:400]}"
            )
        return "\n\n".join(parts)
