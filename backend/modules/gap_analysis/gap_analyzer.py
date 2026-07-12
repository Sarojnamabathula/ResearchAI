"""
ResearchAI — Module 9 & 10: Research Gap Identification + Hypothesis Generator
Analyses a paper collection to find gaps and generate novel hypotheses.
"""

from __future__ import annotations
from typing import List, Dict, Optional
import uuid

from researchai.backend.core.models import (
    Paper, GapAnalysisResult, ResearchGap,
    HypothesisResult, Hypothesis
)
from researchai.backend.core.watsonx_client import get_watsonx_client
from researchai.backend.core.logger import get_logger

logger = get_logger("gap_analysis")

GAP_SYSTEM_PROMPT = """You are a senior research scientist specialised in identifying 
research gaps and open problems in academic literature. Be analytical and specific.
Only identify gaps supported by evidence in the provided papers."""

HYPOTHESIS_SYSTEM_PROMPT = """You are an innovative research scientist who generates 
novel, feasible research hypotheses grounded in existing literature.
Clearly indicate that all hypotheses are AI-generated suggestions."""


class ResearchGapAnalyzer:
    """Identifies research gaps from a paper collection."""

    def __init__(self) -> None:
        self.client = get_watsonx_client()

    def analyze(self, topic: str, papers: List[Paper]) -> GapAnalysisResult:
        logger.info("Gap analysis | topic='%s' | %d papers", topic, len(papers))
        paper_context = self._build_context(papers)

        gap_types = {
            "underexplored_topic": "Topics mentioned but not deeply investigated",
            "missing_dataset": "Lack of standard benchmarks or datasets",
            "weak_methodology": "Methodological weaknesses or lack of rigour",
            "contradictory_findings": "Papers with conflicting conclusions",
            "future_opportunity": "Explicitly stated future work across multiple papers",
        }

        gaps: List[ResearchGap] = []
        for gap_type, description in gap_types.items():
            raw = self.client.generate(
                f"Topic: {topic}\n\nPapers:\n{paper_context[:4000]}\n\n"
                f"Identify ONE specific '{description}' gap in these papers. "
                "If none exists, say 'NONE'. "
                "Format: Title | Description | Why Important | Supporting Papers",
                system_prompt=GAP_SYSTEM_PROMPT,
                max_new_tokens=300,
            )
            if "NONE" in raw.upper():
                continue
            parts = [p.strip() for p in raw.split("|")]
            if len(parts) >= 2:
                gaps.append(ResearchGap(
                    gap_id=str(uuid.uuid4())[:8],
                    title=parts[0] if parts else f"Gap in {gap_type}",
                    description=parts[1] if len(parts) > 1 else raw,
                    importance=parts[2] if len(parts) > 2 else "Important for advancing the field.",
                    gap_type=gap_type,
                    supporting_papers=papers[:3] and [p.id for p in papers[:3]],
                    confidence=0.75,
                ))

        summary = self.client.generate(
            f"Summarise the research gaps found in {len(gaps)} areas for the topic '{topic}'. "
            "Be concise (2-3 sentences).",
            system_prompt=GAP_SYSTEM_PROMPT,
            max_new_tokens=200,
        )

        return GapAnalysisResult(
            topic=topic,
            gaps=gaps,
            summary=summary,
            paper_count_analyzed=len(papers),
        )

    def _build_context(self, papers: List[Paper]) -> str:
        parts = []
        for p in papers:
            parts.append(f"- \"{p.title}\" ({p.year}): {(p.abstract or '')[:300]}")
        return "\n".join(parts)


class HypothesisGenerator:
    """Generates novel research hypotheses from literature gaps."""

    def __init__(self) -> None:
        self.client = get_watsonx_client()

    def generate(
        self, topic: str, papers: List[Paper], gaps: Optional[GapAnalysisResult] = None
    ) -> HypothesisResult:
        logger.info("Generating hypotheses | topic='%s'", topic)
        context = "\n".join(
            f"- \"{p.title}\" ({p.year}): {(p.abstract or '')[:200]}"
            for p in papers[:10]
        )
        gap_context = ""
        if gaps and gaps.gaps:
            gap_context = "\n".join(f"- {g.title}: {g.description}" for g in gaps.gaps[:3])

        keys = ["statement", "motivation", "expected_contribution",
                "novelty", "evaluation_methods"]

        hypotheses: List[Hypothesis] = []
        for i in range(3):  # Generate 3 hypotheses
            prompt = (
                f"Topic: {topic}\n\nExisting Research:\n{context[:3000]}\n\n"
                + (f"Known Gaps:\n{gap_context}\n\n" if gap_context else "")
                + f"Generate hypothesis #{i+1} that is novel and directly addresses "
                "a gap in the literature. Clearly state this is an AI-generated suggestion."
            )
            structured = self.client.generate_structured(
                prompt=prompt,
                output_keys=keys,
                system_prompt=HYPOTHESIS_SYSTEM_PROMPT,
            )
            evals = [
                e.strip() for e in
                structured.get("evaluation_methods", "").split(",")
                if e.strip()
            ]
            hypotheses.append(Hypothesis(
                hypothesis_id=str(uuid.uuid4())[:8],
                statement=structured.get("statement", f"Hypothesis {i+1} for {topic}"),
                motivation=structured.get("motivation", ""),
                expected_contribution=structured.get("expected_contribution", ""),
                novelty=structured.get("novelty", ""),
                evaluation_methods=evals or ["Empirical evaluation", "Benchmark testing"],
                supporting_evidence=[p.id for p in papers[:3]],
                is_ai_generated=True,
                confidence=0.7,
            ))

        return HypothesisResult(topic=topic, hypotheses=hypotheses)
