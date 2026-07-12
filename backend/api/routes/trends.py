"""
Trends API Routes
POST /api/trends/analyze — analyse research trends from paper collection
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

from researchai.backend.core.models import Paper, TrendAnalysis
from researchai.backend.modules.trends.trend_analyzer import TrendAnalyzer
from researchai.backend.db.database import get_paper, list_papers

router = APIRouter()
_analyzer = TrendAnalyzer()


class TrendRequest(BaseModel):
    topic: str
    paper_ids: List[str] = []
    use_all_papers: bool = False


@router.post("/analyze", response_model=TrendAnalysis)
async def analyze_trends(req: TrendRequest):
    """
    Analyse publication trends, keyword frequency, emerging topics,
    most active authors and venues from a paper collection.
    """
    if req.use_all_papers:
        paper_dicts = await list_papers(limit=50)
    else:
        paper_dicts = [await get_paper(pid) for pid in req.paper_ids]
        paper_dicts = [p for p in paper_dicts if p]

    if not paper_dicts:
        raise HTTPException(status_code=400, detail="No papers available for trend analysis")

    papers = [
        Paper(**{k: v for k, v in p.items() if k in Paper.model_fields})
        for p in paper_dicts
    ]
    return _analyzer.analyze(req.topic, papers)
