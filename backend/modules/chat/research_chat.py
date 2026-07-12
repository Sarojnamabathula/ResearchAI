"""
ResearchAI — Module 13: Research Chat
Conversational Q&A over uploaded research papers using RAG.
Maintains session history for multi-turn conversations.
"""

from __future__ import annotations
import uuid
from typing import List, Optional

from researchai.backend.core.models import (
    ChatRequest, ChatResponse, ChatSession, ChatMessage
)
from researchai.backend.core.watsonx_client import get_watsonx_client
from researchai.backend.modules.knowledge_base.vector_store import VectorStore
from researchai.backend.core.logger import get_logger
from researchai.backend.db.database import save_session, get_session

logger = get_logger("research_chat")

SYSTEM_PROMPT = """You are ResearchAI, an expert academic research assistant engaged 
in a conversation about research papers. 

Rules:
1. Answer ONLY from the provided context documents.
2. If information is not in the context, say "This information is not available in the provided papers."
3. Reference specific papers or sections when possible.
4. Maintain conversational coherence — refer to prior turns when relevant.
5. Never fabricate citations, statistics, or findings.
6. When asked to explain complex topics, be thorough but accessible."""


class ResearchChatService:
    """
    Manages multi-turn research conversations with RAG grounding.
    Sessions are persisted to SQLite so conversations can resume.
    """

    def __init__(self, vector_store: VectorStore) -> None:
        self.store = vector_store
        self.client = get_watsonx_client()
        self._sessions: dict = {}  # in-memory session cache

    # ------------------------------------------------------------------
    # Session Management
    # ------------------------------------------------------------------

    def create_session(self, paper_ids: List[str]) -> str:
        """Create a new chat session for the given papers."""
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = ChatSession(
            session_id=session_id,
            paper_ids=paper_ids,
        )
        logger.info("Created session %s for %d papers", session_id, len(paper_ids))
        return session_id

    async def get_or_create_session(
        self, session_id: str, paper_ids: Optional[List[str]] = None
    ) -> ChatSession:
        if session_id in self._sessions:
            return self._sessions[session_id]
        # Try DB
        db_session = await get_session(session_id)
        if db_session:
            session = ChatSession(
                session_id=db_session["id"],
                paper_ids=db_session["paper_ids"],
                messages=[ChatMessage(**m) for m in db_session["messages"]],
            )
            self._sessions[session_id] = session
            return session
        # Create new
        session = ChatSession(
            session_id=session_id,
            paper_ids=paper_ids or [],
        )
        self._sessions[session_id] = session
        return session

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Process a user message and return a grounded AI response."""
        session = await self.get_or_create_session(
            request.session_id, request.paper_ids
        )

        # Retrieve relevant context
        results = self.store.search(
            query=request.message,
            top_k=5,
            paper_ids=session.paper_ids or request.paper_ids or None,
        )

        # Build context string
        context_parts: List[str] = []
        sources_used: List[str] = []
        retrieved_chunks: List[str] = []
        scores: List[float] = []

        for chunk, score in results:
            context_parts.append(
                f"[Paper: {chunk.paper_id} | Section: {chunk.section or 'N/A'}]\n"
                f"{chunk.text}"
            )
            retrieved_chunks.append(chunk.text[:200])
            scores.append(score)
            if chunk.paper_id not in sources_used:
                sources_used.append(chunk.paper_id)

        context_str = "\n\n---\n\n".join(context_parts)

        # Build conversation history (last 6 turns)
        history_text = self._format_history(session.messages[-6:])

        # Build prompt
        prompt = self._build_prompt(
            request.message, context_str, history_text
        )

        # Generate
        answer = self.client.generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            max_new_tokens=768,
        )

        # Update session
        session.messages.append(ChatMessage(role="user", content=request.message))
        session.messages.append(
            ChatMessage(role="assistant", content=answer, sources=sources_used)
        )

        # Persist
        try:
            await save_session(
                session.session_id,
                session.paper_ids,
                [m.dict() for m in session.messages],
            )
        except Exception as exc:
            logger.warning("Session persist failed: %s", exc)

        confidence = round(sum(scores) / len(scores), 3) if scores else 0.0

        return ChatResponse(
            session_id=request.session_id,
            answer=answer,
            sources_used=sources_used,
            retrieved_chunks=retrieved_chunks,
            confidence=confidence,
            reasoning=(
                f"Retrieved {len(results)} chunks from {len(sources_used)} paper(s)."
            ),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _format_history(self, messages: List[ChatMessage]) -> str:
        if not messages:
            return ""
        parts = []
        for m in messages:
            role = "User" if m.role == "user" else "Assistant"
            parts.append(f"{role}: {m.content[:300]}")
        return "\n".join(parts)

    def _build_prompt(
        self, question: str, context: str, history: str
    ) -> str:
        parts: List[str] = []
        if context.strip():
            parts.append(f"=== RESEARCH CONTEXT ===\n{context}")
        if history.strip():
            parts.append(f"=== CONVERSATION HISTORY ===\n{history}")
        parts.append(f"=== CURRENT QUESTION ===\n{question}")
        parts.append("=== ANSWER ===\nProvide a thorough, grounded answer:")
        return "\n\n".join(parts)
