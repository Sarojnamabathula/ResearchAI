"""
Papers API Routes
GET    /api/papers           — list stored papers
GET    /api/papers/{id}      — get a specific paper
POST   /api/papers/process   — process (download + embed) a paper
POST   /api/papers/upload    — upload a local PDF
DELETE /api/papers/{id}      — delete a paper and all its data
"""

from __future__ import annotations
import uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from researchai.backend.core.models import Paper, ExtractedPaper
from researchai.backend.db.database import (
    get_paper, list_papers, save_paper, save_chunks,
    get_chunks_for_paper, delete_paper,
)
from researchai.backend.modules.processing.pdf_processor import PDFProcessor
from researchai.backend.modules.knowledge_base.vector_store import VectorStore
from researchai.backend.core.logger import get_logger
from researchai.config import settings

router = APIRouter()
logger = get_logger("papers_route")
_processor = PDFProcessor()
_store = VectorStore()


class ProcessRequest(BaseModel):
    paper_id: str
    pdf_url: str


@router.get("")
async def list_all_papers(limit: int = 50):
    """List all papers stored in the database."""
    return await list_papers(limit=limit)


@router.get("/{paper_id}")
async def get_paper_by_id(paper_id: str):
    """Get a single paper by its ID."""
    paper = await get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail=f"Paper '{paper_id}' not found")
    return paper


@router.post("/process")
async def process_paper(req: ProcessRequest):
    """
    Download and process a paper's PDF:
    1. Download PDF
    2. Extract text and structure
    3. Generate embeddings
    4. Store in vector database
    """
    try:
        extracted = _processor.process(req.pdf_url, req.paper_id)
        # Store chunks in DB
        await save_chunks([c.dict() for c in extracted.chunks])
        # Index in vector store
        _store.add_chunks(extracted.chunks)
        # Update paper's local_pdf_path
        paper = await get_paper(req.paper_id)
        if paper:
            paper["local_pdf_path"] = str(
                settings.PAPERS_DIR / f"{req.paper_id.replace(':', '_')}.pdf"
            )
            await save_paper(paper)
        return {
            "status": "success",
            "paper_id": req.paper_id,
            "pages": extracted.total_pages,
            "chunks": len(extracted.chunks),
            "sections": list(extracted.sections.keys()),
        }
    except Exception as exc:
        logger.error("Paper processing failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...), paper_id: str = None):
    """
    Upload a local PDF file and process it.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    pid = paper_id or f"upload:{uuid.uuid4().hex[:8]}"
    dest = settings.PAPERS_DIR / f"{pid.replace(':', '_')}.pdf"
    dest.write_bytes(await file.read())

    try:
        extracted = _processor.extract(dest, pid)
        await save_chunks([c.dict() for c in extracted.chunks])
        _store.add_chunks(extracted.chunks)
        return {
            "status": "success",
            "paper_id": pid,
            "filename": file.filename,
            "pages": extracted.total_pages,
            "chunks": len(extracted.chunks),
        }
    except Exception as exc:
        logger.error("Upload processing failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{paper_id}/chunks")
async def get_paper_chunks(paper_id: str):
    """Return all stored text chunks for a paper."""
    chunks = await get_chunks_for_paper(paper_id)
    if not chunks:
        raise HTTPException(status_code=404, detail=f"No chunks found for paper '{paper_id}'")
    return chunks


@router.get("/{paper_id}/knowledge-base/count")
async def knowledge_base_count(paper_id: str):
    """Return total vectors in the knowledge base for a specific paper."""
    return {"paper_id": paper_id, "count": _store.count()}


@router.delete("/{paper_id}")
async def delete_paper_by_id(paper_id: str):
    """
    Delete a paper and all associated data:
    - Removes paper record and chunks from SQLite
    - Removes cached PDF file from disk (if present)
    """
    paper = await get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail=f"Paper '{paper_id}' not found")

    # Remove cached PDF if it exists
    local_path = paper.get("local_pdf_path")
    if local_path:
        pdf_file = Path(local_path)
        if pdf_file.exists():
            try:
                pdf_file.unlink()
            except OSError as exc:
                logger.warning("Could not remove PDF file %s: %s", local_path, exc)

    deleted = await delete_paper(paper_id)
    return {"status": "deleted", "paper_id": paper_id, "found": deleted}
