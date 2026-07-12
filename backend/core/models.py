"""
ResearchAI — Pydantic Data Models
Defines all shared domain models used across backend modules.
"""

from __future__ import annotations
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl


# ---------------------------------------------------------------------------
# Paper / Document Models
# ---------------------------------------------------------------------------

class Author(BaseModel):
    name: str
    affiliation: Optional[str] = None
    orcid: Optional[str] = None


class Paper(BaseModel):
    """Represents a single research paper retrieved from any source."""
    id: str = Field(..., description="Unique identifier (DOI, arXiv ID, etc.)")
    title: str
    authors: List[Author] = []
    abstract: Optional[str] = None
    year: Optional[int] = None
    source: str = Field(..., description="Source API: arxiv | semantic_scholar | crossref | pubmed")
    doi: Optional[str] = None
    url: Optional[str] = None
    pdf_url: Optional[str] = None
    citation_count: Optional[int] = None
    keywords: List[str] = []
    venue: Optional[str] = None
    local_pdf_path: Optional[str] = None
    relevance_score: Optional[float] = None
    added_at: datetime = Field(default_factory=datetime.utcnow)


class PaperChunk(BaseModel):
    """A semantic text chunk extracted from a paper."""
    paper_id: str
    chunk_index: int
    text: str
    section: Optional[str] = None
    page_number: Optional[int] = None
    embedding: Optional[List[float]] = None


class ExtractedPaper(BaseModel):
    """Full structured content of a parsed PDF."""
    paper_id: str
    title: Optional[str] = None
    abstract: Optional[str] = None
    sections: Dict[str, str] = Field(default_factory=dict)
    references: List[str] = []
    figure_captions: List[str] = []
    table_captions: List[str] = []
    full_text: str = ""
    total_pages: int = 0
    chunks: List[PaperChunk] = []


# ---------------------------------------------------------------------------
# Search Models
# ---------------------------------------------------------------------------

class SearchQuery(BaseModel):
    query: str = Field(..., min_length=3, max_length=500)
    max_results: int = Field(default=10, ge=1, le=50)
    sources: List[str] = Field(
        default=["arxiv", "semantic_scholar", "crossref"],
        description="Which sources to search"
    )
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    sort_by: str = Field(default="relevance", pattern="^(relevance|date|citations)$")


class SearchResult(BaseModel):
    query: str
    papers: List[Paper] = []
    total_found: int = 0
    sources_queried: List[str] = []
    search_time_ms: float = 0.0
    keywords_extracted: List[str] = []
    related_concepts: List[str] = []


class QueryAnalysis(BaseModel):
    """NLP analysis of the user's research query."""
    original_query: str
    topic: str
    domain: str
    keywords: List[str] = []
    related_concepts: List[str] = []
    search_expansions: List[str] = []
    intent: str = ""


# ---------------------------------------------------------------------------
# Summarization Models
# ---------------------------------------------------------------------------

class SummaryLevel(str):
    SHORT = "short"
    MEDIUM = "medium"
    DETAILED = "detailed"


class PaperSummary(BaseModel):
    paper_id: str
    title: str
    summary_level: str
    problem_statement: Optional[str] = None
    objective: Optional[str] = None
    methodology: Optional[str] = None
    dataset: Optional[str] = None
    algorithms: Optional[str] = None
    results: Optional[str] = None
    contributions: Optional[str] = None
    limitations: Optional[str] = None
    future_work: Optional[str] = None
    short_summary: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    sources_used: List[str] = []
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Comparison Models
# ---------------------------------------------------------------------------

class ComparisonRequest(BaseModel):
    paper_ids: List[str] = Field(..., min_length=2, max_length=10)
    aspects: List[str] = Field(
        default=["method", "dataset", "results", "limitations", "contributions"]
    )


class PaperComparisonRow(BaseModel):
    paper_id: str
    title: str
    year: Optional[int] = None
    authors: str = ""
    method: Optional[str] = None
    dataset: Optional[str] = None
    accuracy: Optional[str] = None
    metrics: Optional[str] = None
    advantages: Optional[str] = None
    limitations: Optional[str] = None
    contribution: Optional[str] = None


class ComparisonResult(BaseModel):
    papers: List[PaperComparisonRow] = []
    narrative_comparison: str = ""
    key_differences: List[str] = []
    common_ground: List[str] = []
    recommendation: str = ""
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Literature Review Models
# ---------------------------------------------------------------------------

class LiteratureReview(BaseModel):
    topic: str
    abstract: str = ""
    introduction: str = ""
    thematic_sections: Dict[str, str] = Field(default_factory=dict)
    trends: List[str] = []
    strengths: List[str] = []
    weaknesses: List[str] = []
    unresolved_challenges: List[str] = []
    conclusion: str = ""
    references: List[str] = []
    paper_count: int = 0
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Gap Analysis & Hypothesis Models
# ---------------------------------------------------------------------------

class ResearchGap(BaseModel):
    gap_id: str
    title: str
    description: str
    importance: str
    gap_type: str = Field(
        description="underexplored_topic | missing_dataset | weak_methodology | contradictory_findings | future_opportunity"
    )
    supporting_papers: List[str] = []
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class GapAnalysisResult(BaseModel):
    topic: str
    gaps: List[ResearchGap] = []
    summary: str = ""
    paper_count_analyzed: int = 0
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class Hypothesis(BaseModel):
    hypothesis_id: str
    statement: str
    motivation: str
    expected_contribution: str
    novelty: str
    evaluation_methods: List[str] = []
    supporting_evidence: List[str] = []
    is_ai_generated: bool = True
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class HypothesisResult(BaseModel):
    topic: str
    hypotheses: List[Hypothesis] = []
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Citation Models
# ---------------------------------------------------------------------------

class CitationFormat(str):
    APA = "apa"
    IEEE = "ieee"
    MLA = "mla"
    CHICAGO = "chicago"
    BIBTEX = "bibtex"


class Citation(BaseModel):
    paper_id: str
    format: str
    citation_text: str
    bibtex_key: Optional[str] = None


class CitationCollection(BaseModel):
    format: str
    citations: List[Citation] = []
    formatted_references: str = ""
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Report Models
# ---------------------------------------------------------------------------

class ReportRequest(BaseModel):
    topic: str
    paper_ids: List[str] = []
    include_sections: List[str] = Field(
        default=[
            "title", "abstract", "introduction", "background",
            "literature_review", "comparative_analysis",
            "research_gap", "proposed_direction", "references"
        ]
    )
    citation_format: str = "apa"


class ResearchReport(BaseModel):
    title: str
    abstract: str = ""
    introduction: str = ""
    background: str = ""
    literature_review: str = ""
    comparative_analysis: str = ""
    research_gap: str = ""
    proposed_direction: str = ""
    references: List[str] = []
    citation_format: str = "apa"
    paper_count: int = 0
    word_count: int = 0
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Chat Models
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sources: List[str] = []


class ChatSession(BaseModel):
    session_id: str
    paper_ids: List[str] = []
    messages: List[ChatMessage] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(..., min_length=1, max_length=2000)
    paper_ids: List[str] = []


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sources_used: List[str] = []
    retrieved_chunks: List[str] = []
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reasoning: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Timeline Models
# ---------------------------------------------------------------------------

class TimelineEvent(BaseModel):
    year: int
    title: str
    description: str
    paper_id: Optional[str] = None
    significance: str = ""


class ResearchTimeline(BaseModel):
    topic: str
    events: List[TimelineEvent] = []
    narrative: str = ""
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Trend Models
# ---------------------------------------------------------------------------

class TrendData(BaseModel):
    label: str
    values: List[int] = []
    years: List[int] = []


class TrendAnalysis(BaseModel):
    topic: str
    publication_trends: List[TrendData] = []
    top_keywords: List[Dict[str, Any]] = []
    emerging_topics: List[str] = []
    most_active_authors: List[Dict[str, Any]] = []
    most_active_venues: List[Dict[str, Any]] = []
    growth_rate: float = 0.0
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# RAG / Explainability Models
# ---------------------------------------------------------------------------

class RAGContext(BaseModel):
    query: str
    retrieved_chunks: List[PaperChunk] = []
    source_paper_ids: List[str] = []
    retrieval_scores: List[float] = []


class ExplainableResponse(BaseModel):
    answer: str
    reasoning_summary: str = ""
    sources_used: List[str] = []
    retrieved_documents: List[str] = []
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    model_used: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    generated_at: datetime = Field(default_factory=datetime.utcnow)
