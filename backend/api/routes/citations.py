"""
Citations API Routes
POST /api/citations/generate   — generate citations for papers
POST /api/citations/collection — full reference list
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

from researchai.backend.core.models import Paper, CitationCollection
from researchai.backend.modules.citation.citation_manager import CitationManager
from researchai.backend.db.database import get_paper, list_papers

router = APIRouter()
_manager = CitationManager()


class CitationRequest(BaseModel):
    paper_ids: List[str]
    format: str = "apa"


@router.post("/generate", response_model=CitationCollection)
async def generate_citations(req: CitationRequest):
    """
    Generate citations in APA, IEEE, MLA, Chicago, or BibTeX format.
    Only papers stored in the database can be cited.
    """
    if req.format not in CitationManager.SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format. Choose from: {CitationManager.SUPPORTED_FORMATS}"
        )

    papers: List[Paper] = []
    for pid in req.paper_ids:
        p_dict = await get_paper(pid)
        if not p_dict:
            raise HTTPException(status_code=404, detail=f"Paper '{pid}' not found")
        papers.append(Paper(**{k: v for k, v in p_dict.items() if k in Paper.model_fields}))

    return _manager.generate_collection(papers, req.format)


@router.get("/formats")
async def list_formats():
    """List all supported citation formats."""
    return {"formats": CitationManager.SUPPORTED_FORMATS}
