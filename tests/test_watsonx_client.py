"""
Tests for WatsonxClient stub behavior (no credentials needed).
"""

import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def clear_singleton():
    """Reset the WatsonxClient singleton between tests."""
    from researchai.backend.core import watsonx_client as wm
    wm.WatsonxClient._instance = None
    yield
    wm.WatsonxClient._instance = None


class TestWatsonxClientStub:
    """These tests run without real watsonx credentials — stub mode only."""

    def test_stub_response_when_no_credentials(self):
        with patch("researchai.config.settings.WATSONX_API_KEY", ""):
            with patch("researchai.config.settings.WATSONX_PROJECT_ID", ""):
                from researchai.backend.core.watsonx_client import WatsonxClient
                client = WatsonxClient()
                client._model = None  # force stub
                response = client.generate("Test prompt")
                assert "STUB" in response or "watsonx" in response.lower()

    def test_embed_returns_zero_vectors_without_credentials(self):
        from researchai.backend.core.watsonx_client import WatsonxClient
        client = WatsonxClient()
        client._model = None  # force stub
        embeddings = client.embed(["hello", "world"])
        assert len(embeddings) == 2
        assert all(isinstance(v, list) for v in embeddings)
        # All zeros when no model
        assert all(x == 0.0 for x in embeddings[0])

    def test_generate_structured_returns_dict_with_all_keys(self):
        from researchai.backend.core.watsonx_client import WatsonxClient
        client = WatsonxClient()
        client._model = None  # force stub
        # generate() returns stub string, _parse_structured should return empty dict
        result = client.generate_structured(
            "Analyse: deep learning",
            output_keys=["topic", "domain", "keywords"],
        )
        assert isinstance(result, dict)
        assert "topic" in result
        assert "domain" in result
        assert "keywords" in result

    def test_parse_structured_extracts_values(self):
        from researchai.backend.core.watsonx_client import WatsonxClient
        raw = "topic: Large Language Models\ndomain: Computer Science\nkeywords: LLM, GPT"
        result = WatsonxClient._parse_structured(raw, ["topic", "domain", "keywords"])
        assert result["topic"] == "Large Language Models"
        assert result["domain"] == "Computer Science"
        assert "LLM" in result["keywords"]

    def test_parse_structured_handles_missing_keys(self):
        from researchai.backend.core.watsonx_client import WatsonxClient
        raw = "topic: AI\n"
        result = WatsonxClient._parse_structured(raw, ["topic", "domain", "keywords"])
        assert result["topic"] == "AI"
        assert result["domain"] == ""
        assert result["keywords"] == ""

    def test_build_prompt_without_system(self):
        from researchai.backend.core.watsonx_client import WatsonxClient
        prompt = WatsonxClient._build_prompt("Hello", None)
        assert "<|user|>" in prompt
        assert "<|assistant|>" in prompt
        assert "Hello" in prompt

    def test_build_prompt_with_system(self):
        from researchai.backend.core.watsonx_client import WatsonxClient
        prompt = WatsonxClient._build_prompt("Hello", "You are a researcher.")
        assert "<|system|>" in prompt
        assert "You are a researcher." in prompt
        assert "Hello" in prompt

    def test_singleton_pattern(self):
        from researchai.backend.core.watsonx_client import WatsonxClient, get_watsonx_client
        c1 = WatsonxClient()
        c2 = get_watsonx_client()
        assert c1 is c2
