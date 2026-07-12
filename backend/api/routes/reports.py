"""
Reports API Routes
POST /api/reports/generate — generate a full research report
GET  /api/reports          — list all generated reports
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional

from researchai.backend.core.models import Paper, ReportRequest, ResearchReport
from researchai.backend.modules.report.report_generator import ReportGenerator
from researchai.backend.db.database import get_paper, list_papers, save_report, list_reports

router = APIRouter()
_generator = ReportGenerator()


@router.post("/generate", response_model=ResearchReport)
async def generate_report(req: ReportRequest):
    """
    Generate a comprehensive academic research report combining:
    literature review, comparative analysis, gap identification,
    proposed research directions, and formatted references.
    """
    paper_dicts: List[dict] = []

    if req.paper_ids:
        for pid in req.paper_ids:
            p = await get_paper(pid)
            if p:
                paper_dicts.append(p)
    else:
        paper_dicts = await list_papers(limit=25)

    if not paper_dicts:
        raise HTTPException(
            status_code=400,
            detail="No papers available. Search for papers first."
        )

    papers = [
        Paper(**{k: v for k, v in p.items() if k in Paper.model_fields})
        for p in paper_dicts
    ]

    report = _generator.generate(req, papers, {p.id: None for p in papers})

    # Persist report
    await save_report(req.topic, report.dict())

    return report


@router.get("")
async def list_all_reports():
    """List all previously generated research reports."""
    return await list_reports()
