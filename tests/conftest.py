"""
ResearchAI — Test Suite
Pytest configuration and shared fixtures.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock


# ── Async test support ────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    """Provide a single asyncio event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ── Shared mock fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def mock_watsonx_client():
    """Mock WatsonxClient that returns deterministic stub responses."""
    client = MagicMock()
    client.generate.return_value = (
        "topic: Large Language Models\n"
        "domain: Computer Science\n"
        "keywords: LLM, transformer, GPT, BERT, language model\n"
        "related_concepts: NLP, deep learning, attention mechanism\n"
        "search_expansions: large language models, transformer-based models\n"
        "intent: find_papers"
    )
    client.generate_structured.return_value = {
        "topic": "Large Language Models",
        "domain": "Computer Science",
        "keywords": "LLM, transformer, GPT",
        "related_concepts": "NLP, deep learning",
        "search_expansions": "large language models",
        "intent": "find_papers",
    }
    client.embed.return_value = [[0.1] * 384, [0.2] * 384]
    return client


@pytest.fixture
def sample_paper():
    """A sample Paper dict for use in tests."""
    return {
        "id": "arxiv:test.001",
        "title": "Attention Is All You Need",
        "authors": [{"name": "Vaswani, A."}],
        "abstract": "We propose a new network architecture, the Transformer.",
        "year": 2017,
        "source": "arxiv",
        "doi": "10.48550/arXiv.1706.03762",
        "url": "https://arxiv.org/abs/1706.03762",
        "pdf_url": "https://arxiv.org/pdf/1706.03762",
        "citation_count": 80000,
        "keywords": ["transformer", "attention", "NLP"],
        "venue": "NIPS 2017",
        "local_pdf_path": None,
        "relevance_score": 0.95,
    }
