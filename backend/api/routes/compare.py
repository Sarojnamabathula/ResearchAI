"""
Comparison API Routes
POST /api/compare — compare multiple papers
"""

from fastapi import APIRouter, HTTPException
from typing import List

from researchai.backend.core.models import Paper, ComparisonRequest, ComparisonResult
from researchai.backend.modules.comparison.comparator import PaperComparator
from researchai.backend.db.database import get_paper

router = APIRouter()
_comparator = PaperComparator()


@router.post("", response_model=ComparisonResult)
async def compare_papers(req: ComparisonRequest):
    """
    Compare 2–10 papers across methodology, dataset, results, and contributions.
    Returns a structured comparison table and narrative analysis.
    """
    if len(req.paper_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 paper IDs required")

    papers: List[Paper] = []
    for pid in req.paper_ids:
        p_dict = await get_paper(pid)
        if not p_dict:
            raise HTTPException(status_code=404, detail=f"Paper '{pid}' not found")
        papers.append(Paper(**{k: v for k, v in p_dict.items() if k in Paper.model_fields}))

    return _comparator.compare(papers=papers, extracted={p.id: None for p in papers})
