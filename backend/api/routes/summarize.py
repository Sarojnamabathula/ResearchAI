"""
Summarization API Routes
POST /api/summarize — generate a structured paper summary
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from researchai.backend.core.models import Paper, PaperSummary
from researchai.backend.modules.summarization.summarizer import PaperSummarizer
from researchai.backend.db.database import get_paper

router = APIRouter()
_summarizer = PaperSummarizer()


class SummarizeRequest(BaseModel):
    paper_id: str
    level: str = "medium"  # short | medium | detailed


@router.post("", response_model=PaperSummary)
async def summarize_paper(req: SummarizeRequest):
    """
    Generate a structured summary of a research paper.
    Level options: short (3 sentences), medium (key aspects), detailed (full analysis).
    """
    paper_dict = await get_paper(req.paper_id)
    if not paper_dict:
        raise HTTPException(status_code=404, detail=f"Paper '{req.paper_id}' not found")

    paper = Paper(**{
        k: v for k, v in paper_dict.items()
        if k in Paper.model_fields
    })

    if req.level not in ("short", "medium", "detailed"):
        raise HTTPException(status_code=400, detail="Level must be: short | medium | detailed")

    return _summarizer.summarize(paper=paper, extracted=None, level=req.level)
