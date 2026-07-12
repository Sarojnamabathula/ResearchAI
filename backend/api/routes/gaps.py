"""
Gap Analysis & Hypothesis API Routes
POST /api/gaps/analyze     — identify research gaps
POST /api/gaps/hypotheses  — generate research hypotheses
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from researchai.backend.core.models import Paper, GapAnalysisResult, HypothesisResult
from researchai.backend.modules.gap_analysis.gap_analyzer import (
    ResearchGapAnalyzer, HypothesisGenerator
)
from researchai.backend.db.database import get_paper, list_papers

router = APIRouter()
_gap_analyzer = ResearchGapAnalyzer()
_hyp_generator = HypothesisGenerator()


class GapRequest(BaseModel):
    topic: str
    paper_ids: List[str] = []
    use_all_papers: bool = False


@router.post("/analyze", response_model=GapAnalysisResult)
async def analyze_gaps(req: GapRequest):
    """
    Analyse a paper collection and identify research gaps:
    underexplored topics, missing datasets, weak methodologies, contradictions.
    """
    papers = await _load_papers(req.paper_ids, req.use_all_papers)
    if not papers:
        raise HTTPException(status_code=400, detail="No papers available for analysis")
    return _gap_analyzer.analyze(req.topic, papers)


@router.post("/hypotheses", response_model=HypothesisResult)
async def generate_hypotheses(req: GapRequest):
    """
    Generate AI-powered research hypotheses based on identified gaps.
    All hypotheses are clearly marked as AI-generated suggestions.
    """
    papers = await _load_papers(req.paper_ids, req.use_all_papers)
    if not papers:
        raise HTTPException(status_code=400, detail="No papers available")
    gaps = _gap_analyzer.analyze(req.topic, papers)
    return _hyp_generator.generate(req.topic, papers, gaps)


async def _load_papers(paper_ids: List[str], use_all: bool) -> List[Paper]:
    if use_all:
        dicts = await list_papers(limit=20)
    else:
        dicts = []
        for pid in paper_ids:
            p = await get_paper(pid)
            if p:
                dicts.append(p)
    return [Paper(**{k: v for k, v in d.items() if k in Paper.model_fields}) for d in dicts]
