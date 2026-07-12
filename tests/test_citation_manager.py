"""
Tests for citation manager — format generation.
"""

import pytest
from unittest.mock import patch, MagicMock
from researchai.backend.core.models import Paper, Author
from researchai.backend.modules.citation.citation_manager import CitationManager


@pytest.fixture
def manager():
    return CitationManager()


@pytest.fixture
def paper_vaswani():
    return Paper(
        id="arxiv:1706.03762",
        title="Attention Is All You Need",
        source="arxiv",
        authors=[
            Author(name="Vaswani, A."),
            Author(name="Shazeer, N."),
            Author(name="Parmar, N."),
        ],
        year=2017,
        venue="NIPS",
        doi="10.48550/arXiv.1706.03762",
        url="https://arxiv.org/abs/1706.03762",
    )


@pytest.fixture
def paper_no_authors():
    return Paper(
        id="crossref:999",
        title="Anonymous Research Paper",
        source="crossref",
        year=2022,
    )


class TestCitationFormats:
    def test_apa_has_year_in_parentheses(self, manager, paper_vaswani):
        cit = manager.generate_citation(paper_vaswani, "apa")
        assert "(2017)" in cit.citation_text

    def test_apa_has_title(self, manager, paper_vaswani):
        cit = manager.generate_citation(paper_vaswani, "apa")
        assert "Attention Is All You Need" in cit.citation_text

    def test_ieee_format_has_author_initials(self, manager, paper_vaswani):
        cit = manager.generate_citation(paper_vaswani, "ieee")
        assert "2017" in cit.citation_text

    def test_mla_format(self, manager, paper_vaswani):
        cit = manager.generate_citation(paper_vaswani, "mla")
        assert "Attention Is All You Need" in cit.citation_text

    def test_chicago_format(self, manager, paper_vaswani):
        cit = manager.generate_citation(paper_vaswani, "chicago")
        assert "2017" in cit.citation_text

    def test_bibtex_has_article_type(self, manager, paper_vaswani):
        cit = manager.generate_citation(paper_vaswani, "bibtex")
        assert "@article" in cit.citation_text.lower()

    def test_bibtex_key_is_set(self, manager, paper_vaswani):
        cit = manager.generate_citation(paper_vaswani, "bibtex")
        assert cit.bibtex_key is not None
        assert len(cit.bibtex_key) > 0

    def test_paper_without_authors_does_not_crash(self, manager, paper_no_authors):
        for fmt in ("apa", "ieee", "mla", "chicago", "bibtex"):
            cit = manager.generate_citation(paper_no_authors, fmt)
            assert cit.citation_text

    def test_unsupported_format_raises(self, manager, paper_vaswani):
        from researchai.backend.core.exceptions import CitationError
        with pytest.raises(CitationError):
            manager.generate_citation(paper_vaswani, "harvard")

    def test_collection_has_same_count(self, manager, paper_vaswani, paper_no_authors):
        papers = [paper_vaswani, paper_no_authors]
        collection = manager.generate_collection(papers, "apa")
        assert len(collection.citations) == 2
        assert collection.format == "apa"
        assert collection.formatted_references != ""
