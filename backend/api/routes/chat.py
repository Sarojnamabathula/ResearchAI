"""
Chat API Routes
POST /api/chat/session  — create a new chat session
POST /api/chat/message  — send a message
GET  /api/chat/{id}     — get session history
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

from researchai.backend.core.models import ChatRequest, ChatResponse
from researchai.backend.modules.chat.research_chat import ResearchChatService
from researchai.backend.modules.knowledge_base.vector_store import VectorStore
from researchai.backend.db.database import get_session

router = APIRouter()
_store = VectorStore()
_chat_service = ResearchChatService(vector_store=_store)


class SessionRequest(BaseModel):
    paper_ids: List[str] = []


@router.post("/session")
async def create_session(req: SessionRequest):
    """Create a new research chat session scoped to the specified papers."""
    session_id = _chat_service.create_session(req.paper_ids)
    return {"session_id": session_id, "paper_ids": req.paper_ids}


@router.post("/message", response_model=ChatResponse)
async def send_message(req: ChatRequest):
    """
    Send a research question and receive a grounded answer from IBM Granite.
    The response includes source attribution, retrieved chunks, and confidence.
    """
    return await _chat_service.chat(req)


@router.get("/{session_id}")
async def get_chat_session(session_id: str):
    """Retrieve the full message history of a chat session."""
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return session
