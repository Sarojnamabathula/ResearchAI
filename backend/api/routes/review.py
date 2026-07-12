"""
Literature Review API Routes
POST /api/review — generate a literature review
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

from researchai.backend.core.models import Paper, LiteratureReview
from researchai.backend.modules.literature_review.review_generator import LiteratureReviewGenerator
from researchai.backend.db.database import get_paper, list_papers

router = APIRouter()
_generator = LiteratureReviewGenerator()


class ReviewRequest(BaseModel):
    topic: str
    paper_ids: List[str] = []
    use_all_papers: bool = False


@router.post("", response_model=LiteratureReview)
async def generate_literature_review(req: ReviewRequest):
    """
    Automatically generate a coherent academic literature review.
    Provide specific paper_ids or set use_all_papers=true to use the full library.
    """
    if req.use_all_papers:
        paper_dicts = await list_papers(limit=30)
    else:
        paper_dicts = []
        for pid in req.paper_ids:
            p = await get_paper(pid)
            if p:
                paper_dicts.append(p)

    if not paper_dicts:
        raise HTTPException(
            status_code=400,
            detail="No papers found. Search and process papers first."
        )

    papers = [
        Paper(**{k: v for k, v in p.items() if k in Paper.model_fields})
        for p in paper_dicts
    ]
    return _generator.generate(req.topic, papers, {p.id: None for p in papers})
