"""
Tests for QueryAnalyzer — stub behavior.
"""

import pytest
from unittest.mock import patch, MagicMock
from researchai.backend.core.models import QueryAnalysis


class TestQueryAnalyzer:
    @pytest.fixture
    def analyzer_with_stub_client(self):
        from researchai.backend.modules.search.query_analyzer import QueryAnalyzer
        with patch(
            "researchai.backend.modules.search.query_analyzer.get_watsonx_client"
        ) as mock_get:
            mock_client = MagicMock()
            mock_client.generate_structured.return_value = {
                "topic": "Large Language Models",
                "domain": "Computer Science",
                "keywords": "LLM, transformer, GPT, attention",
                "related_concepts": "NLP, deep learning, BERT",
                "search_expansions": "large language model, foundation model",
                "intent": "find_papers",
            }
            mock_get.return_value = mock_client
            yield QueryAnalyzer()

    def test_analyze_returns_query_analysis(self, analyzer_with_stub_client):
        result = analyzer_with_stub_client.analyze("Latest advances in large language models")
        assert isinstance(result, QueryAnalysis)

    def test_analyze_extracts_keywords(self, analyzer_with_stub_client):
        result = analyzer_with_stub_client.analyze("LLM applications")
        assert len(result.keywords) > 0
        assert "LLM" in result.keywords or "transformer" in result.keywords

    def test_analyze_extracts_domain(self, analyzer_with_stub_client):
        result = analyzer_with_stub_client.analyze("deep learning for NLP")
        assert result.domain == "Computer Science"

    def test_analyze_extracts_intent(self, analyzer_with_stub_client):
        result = analyzer_with_stub_client.analyze("find papers on federated learning")
        assert result.intent == "find_papers"

    def test_analyze_preserves_original_query(self, analyzer_with_stub_client):
        query = "survey of transformer architectures"
        result = analyzer_with_stub_client.analyze(query)
        assert result.original_query == query

    def test_split_list_helper(self):
        from researchai.backend.modules.search.query_analyzer import QueryAnalyzer
        qa = QueryAnalyzer.__new__(QueryAnalyzer)
        result = qa._split_list("alpha, beta, gamma , delta")
        assert result == ["alpha", "beta", "gamma", "delta"]

    def test_split_list_empty_string(self):
        from researchai.backend.modules.search.query_analyzer import QueryAnalyzer
        qa = QueryAnalyzer.__new__(QueryAnalyzer)
        result = qa._split_list("")
        assert result == []
