"""
ResearchAI — Module 14: Research Timeline Generator
Creates chronological research timelines showing the evolution of a topic.
"""

from __future__ import annotations
from typing import List

from researchai.backend.core.models import Paper, ResearchTimeline, TimelineEvent
from researchai.backend.core.watsonx_client import get_watsonx_client
from researchai.backend.core.logger import get_logger

logger = get_logger("timeline")

SYSTEM_PROMPT = """You are a research historian specialising in tracing the evolution
of scientific fields. Identify key milestones and breakthroughs chronologically."""


class TimelineGenerator:
    """
    Generates a chronological research timeline from a paper collection.
    Identifies key milestones, breakthroughs, and paradigm shifts.
    """

    def __init__(self) -> None:
        self.client = get_watsonx_client()

    def generate(self, topic: str, papers: List[Paper]) -> ResearchTimeline:
        logger.info("Generating timeline | topic='%s' | %d papers", topic, len(papers))

        # Sort papers by year
        sorted_papers = sorted(
            [p for p in papers if p.year],
            key=lambda p: p.year,
        )

        # Build per-paper events from actual papers
        events: List[TimelineEvent] = []
        for p in sorted_papers:
            # Quick significance assessment
            significance = self.client.generate(
                f"In one sentence, state why this paper was significant to {topic}: "
                f"'{p.title}' ({p.year}). Abstract: {(p.abstract or '')[:300]}",
                system_prompt=SYSTEM_PROMPT,
                max_new_tokens=100,
            )
            events.append(TimelineEvent(
                year=p.year,
                title=p.title,
                description=(p.abstract or "")[:200],
                paper_id=p.id,
                significance=significance.strip(),
            ))

        # Also add historical milestones via AI
        milestone_prompt = (
            f"List 5 major historical milestones in the evolution of '{topic}' "
            "that are NOT covered by these papers. Format: YEAR | Title | Description\n\n"
            f"Papers covered: {[p.title for p in sorted_papers[:5]]}"
        )
        milestones_raw = self.client.generate(
            milestone_prompt, system_prompt=SYSTEM_PROMPT, max_new_tokens=400
        )

        for line in milestones_raw.splitlines():
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3 and parts[0].isdigit():
                try:
                    events.append(TimelineEvent(
                        year=int(parts[0]),
                        title=parts[1],
                        description=parts[2],
                        significance="Historical milestone",
                    ))
                except (ValueError, IndexError):
                    continue

        # Sort all events
        events_sorted = sorted(events, key=lambda e: e.year)

        # Narrative
        narrative = self.client.generate(
            f"Write a 250-word narrative describing the evolution of '{topic}' "
            "from early beginnings to the present, covering these milestones:\n"
            + "\n".join(f"- {e.year}: {e.title}" for e in events_sorted[:10]),
            system_prompt=SYSTEM_PROMPT,
            max_new_tokens=400,
        )

        return ResearchTimeline(
            topic=topic,
            events=events_sorted,
            narrative=narrative,
        )
