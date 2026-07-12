"""
Timeline API Routes
POST /api/timeline/generate — generate a research evolution timeline
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

from researchai.backend.core.models import Paper, ResearchTimeline
from researchai.backend.modules.timeline.timeline_generator import TimelineGenerator
from researchai.backend.db.database import get_paper, list_papers

router = APIRouter()
_generator = TimelineGenerator()


class TimelineRequest(BaseModel):
    topic: str
    paper_ids: List[str] = []
    use_all_papers: bool = False


@router.post("/generate", response_model=ResearchTimeline)
async def generate_timeline(req: TimelineRequest):
    """
    Generate a chronological research timeline showing the evolution of a topic.
    Events are derived from retrieved papers and AI-generated historical milestones.
    """
    if req.use_all_papers:
        paper_dicts = await list_papers(limit=30)
    else:
        paper_dicts = [
            await get_paper(pid) for pid in req.paper_ids
        ]
        paper_dicts = [p for p in paper_dicts if p]

    if not paper_dicts:
        raise HTTPException(status_code=400, detail="No papers found for timeline generation")

    papers = [
        Paper(**{k: v for k, v in p.items() if k in Paper.model_fields})
        for p in paper_dicts
    ]
    return _generator.generate(req.topic, papers)
