"""
Tests for core data models (Pydantic).
"""

import pytest
from datetime import datetime
from researchai.backend.core.models import (
    Paper, Author, PaperChunk, SearchQuery, SearchResult,
    QueryAnalysis, PaperSummary, ComparisonRequest,
    Citation, CitationCollection, ChatMessage, ChatRequest,
    ResearchGap, GapAnalysisResult, Hypothesis, HypothesisResult,
    TimelineEvent, ResearchTimeline, TrendData, TrendAnalysis,
    RAGContext, ExplainableResponse,
)


# ── Paper Models ──────────────────────────────────────────────────────────────

class TestPaperModel:
    def test_paper_creates_with_required_fields(self):
        p = Paper(id="arxiv:001", title="Test Paper", source="arxiv")
        assert p.id == "arxiv:001"
        assert p.title == "Test Paper"
        assert p.authors == []
        assert p.keywords == []
        assert isinstance(p.added_at, datetime)

    def test_paper_accepts_full_metadata(self):
        p = Paper(
            id="doi:10.1234",
            title="Full Paper",
            source="crossref",
            authors=[Author(name="Smith, J.")],
            year=2023,
            citation_count=42,
            venue="NeurIPS",
            relevance_score=0.9,
        )
        assert p.year == 2023
        assert p.citation_count == 42
        assert len(p.authors) == 1
        assert p.authors[0].name == "Smith, J."

    def test_author_model(self):
        a = Author(name="Turing, A.M.", affiliation="Manchester", orcid="0000-0000-0000-0001")
        assert a.name == "Turing, A.M."
        assert a.affiliation == "Manchester"

    def test_paper_chunk(self):
        chunk = PaperChunk(paper_id="arxiv:001", chunk_index=0, text="Hello world")
        assert chunk.chunk_index == 0
        assert chunk.embedding is None


# ── Search Models ─────────────────────────────────────────────────────────────

class TestSearchModels:
    def test_search_query_validation(self):
        q = SearchQuery(query="deep learning for NLP")
        assert q.max_results == 10
        assert "arxiv" in q.sources
        assert q.sort_by == "relevance"

    def test_search_query_rejects_short_query(self):
        with pytest.raises(Exception):
            SearchQuery(query="ab")  # min_length=3

    def test_search_query_rejects_invalid_sort(self):
        with pytest.raises(Exception):
            SearchQuery(query="deep learning", sort_by="random")

    def test_search_result_defaults(self):
        r = SearchResult(query="test")
        assert r.papers == []
        assert r.total_found == 0

    def test_query_analysis_fields(self):
        a = QueryAnalysis(
            original_query="LLMs in healthcare",
            topic="Large Language Models",
            domain="Healthcare",
            keywords=["LLM", "healthcare", "NLP"],
        )
        assert a.domain == "Healthcare"
        assert "LLM" in a.keywords


# ── Citation Models ───────────────────────────────────────────────────────────

class TestCitationModels:
    def test_citation_creation(self):
        c = Citation(
            paper_id="arxiv:001",
            format="apa",
            citation_text="Smith, J. (2023). A paper. Journal.",
        )
        assert c.format == "apa"

    def test_citation_collection(self):
        cc = CitationCollection(
            format="ieee",
            citations=[
                Citation(paper_id="p1", format="ieee", citation_text="A. Smith..."),
            ],
        )
        assert len(cc.citations) == 1
        assert isinstance(cc.generated_at, datetime)


# ── Chat Models ───────────────────────────────────────────────────────────────

class TestChatModels:
    def test_chat_message_roles(self):
        for role in ("user", "assistant", "system"):
            m = ChatMessage(role=role, content="test")
            assert m.role == role

    def test_chat_message_rejects_invalid_role(self):
        with pytest.raises(Exception):
            ChatMessage(role="bot", content="test")

    def test_chat_request_length_limit(self):
        with pytest.raises(Exception):
            ChatRequest(session_id="s1", message="x" * 2001)


# ── Gap Analysis Models ───────────────────────────────────────────────────────

class TestGapModels:
    def test_research_gap_fields(self):
        g = ResearchGap(
            gap_id="g1",
            title="Sparse datasets",
            description="Few labelled datasets exist.",
            importance="Limits model evaluation.",
            gap_type="missing_dataset",
        )
        assert g.gap_type == "missing_dataset"
        assert g.confidence == 0.0

    def test_hypothesis_is_ai_generated_flag(self):
        h = Hypothesis(
            hypothesis_id="h1",
            statement="X improves Y",
            motivation="Because of Z",
            expected_contribution="Better accuracy",
            novelty="New combination",
        )
        assert h.is_ai_generated is True


# ── Timeline / Trend Models ───────────────────────────────────────────────────

class TestTimelineTrendModels:
    def test_timeline_event(self):
        e = TimelineEvent(year=2017, title="Transformer", description="Vaswani et al.")
        assert e.year == 2017

    def test_trend_data(self):
        td = TrendData(label="Publications", values=[5, 10, 15], years=[2021, 2022, 2023])
        assert len(td.values) == 3

    def test_trend_analysis_defaults(self):
        ta = TrendAnalysis(topic="AI")
        assert ta.growth_rate == 0.0
        assert ta.publication_trends == []


# ── RAG Models ────────────────────────────────────────────────────────────────

class TestRAGModels:
    def test_explainable_response_confidence_bounds(self):
        with pytest.raises(Exception):
            ExplainableResponse(answer="test", confidence=1.5)

    def test_explainable_response_defaults(self):
        er = ExplainableResponse(answer="Test answer")
        assert er.confidence == 0.0
        assert er.sources_used == []

    def test_rag_context(self):
        ctx = RAGContext(query="What is attention?")
        assert ctx.retrieved_chunks == []
        assert ctx.source_paper_ids == []
