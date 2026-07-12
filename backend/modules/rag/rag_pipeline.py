"""
ResearchAI — Module 5: RAG Pipeline
Retrieval-Augmented Generation using IBM Granite.
Grounded, explainable responses with source attribution.
"""

from __future__ import annotations
from typing import List, Optional

from researchai.backend.core.models import ExplainableResponse, RAGContext
from researchai.backend.core.watsonx_client import get_watsonx_client
from researchai.backend.modules.knowledge_base.knowledge_base import KnowledgeBase
from researchai.backend.core.logger import get_logger

logger = get_logger("rag_pipeline")

SYSTEM_PROMPT = """You are ResearchAI, an expert academic research assistant.
Your task is to answer research questions accurately and clearly.

Rules:
1. Base every answer strictly on the provided context documents.
2. If the context does not contain enough information, say so clearly.
3. Never fabricate citations, paper titles, or statistics.
4. Always reference which source (paper) supports each claim.
5. Use precise academic language.
6. Be concise but thorough."""


class RAGPipeline:
    """
    Retrieval-Augmented Generation pipeline.
    
    Flow:
      query → semantic_search → context assembly → Granite prompt → response
    """

    def __init__(self, knowledge_base: KnowledgeBase) -> None:
        self.kb = knowledge_base
        self.client = get_watsonx_client()

    def answer(
        self,
        query: str,
        paper_ids: Optional[List[str]] = None,
        n_context_chunks: int = 5,
    ) -> ExplainableResponse:
        """Answer a research question using RAG."""
        logger.info("RAG query: %s", query[:80])

        # Step 1: Retrieve relevant context
        rag_ctx: RAGContext = self.kb.semantic_search(
            query=query,
            n_results=n_context_chunks,
            paper_ids=paper_ids,
        )

        # Step 2: Build context string
        context_parts: List[str] = []
        for i, chunk in enumerate(rag_ctx.retrieved_chunks):
            context_parts.append(
                f"[Source {i+1} — Paper: {chunk.paper_id}, Section: {chunk.section or 'N/A'}]\n"
                f"{chunk.text}"
            )
        context_str = "\n\n---\n\n".join(context_parts)

        # Step 3: Build prompt
        prompt = self._build_rag_prompt(query, context_str)

        # Step 4: Generate
        raw_answer = self.client.generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            max_new_tokens=1024,
        )

        # Step 5: Build explainable response
        confidence = self._estimate_confidence(rag_ctx)
        reasoning = self._build_reasoning(rag_ctx, query)

        return ExplainableResponse(
            answer=raw_answer,
            reasoning_summary=reasoning,
            sources_used=rag_ctx.source_paper_ids,
            retrieved_documents=[c.text[:200] for c in rag_ctx.retrieved_chunks],
            confidence=confidence,
            model_used=f"ibm/{self._get_model_name()}",
            generated_at=__import__("datetime").datetime.utcnow(),
        )

    def _build_rag_prompt(self, query: str, context: str) -> str:
        if not context.strip():
            return (
                f"The user asked: '{query}'\n"
                "No relevant documents are available in the knowledge base. "
                "Politely inform the user and suggest they search or upload papers first."
            )
        return (
            "Use the following research documents to answer the question.\n\n"
            f"=== CONTEXT DOCUMENTS ===\n{context}\n\n"
            f"=== QUESTION ===\n{query}\n\n"
            "=== ANSWER ===\n"
            "Provide a thorough, grounded answer referencing the source numbers above:"
        )

    def _estimate_confidence(self, ctx: RAGContext) -> float:
        """Simple confidence heuristic based on retrieval scores."""
        if not ctx.retrieval_scores:
            return 0.0
        avg = sum(ctx.retrieval_scores) / len(ctx.retrieval_scores)
        # Clamp to [0, 1]
        return round(min(max(avg, 0.0), 1.0), 3)

    def _build_reasoning(self, ctx: RAGContext, query: str) -> str:
        count = len(ctx.retrieved_chunks)
        sources = list(set(c.paper_id for c in ctx.retrieved_chunks))
        return (
            f"Retrieved {count} relevant chunks from {len(sources)} paper(s). "
            f"Papers used: {', '.join(sources[:5])}. "
            f"Query: '{query[:60]}'"
        )

    def _get_model_name(self) -> str:
        from researchai.config import settings
        return settings.GRANITE_MODEL_ID.split("/")[-1]
