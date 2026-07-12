"""
Tests for SearchEngine — deduplication and ranking logic.
"""

import pytest
from researchai.backend.core.models import Paper, SearchQuery
from researchai.backend.modules.search.search_engine import SearchEngine


def make_paper(title: str, year: int = 2020, citations: int = 0, source: str = "arxiv") -> Paper:
    return Paper(id=f"test:{title[:8]}", title=title, source=source, year=year, citation_count=citations)


class TestDeduplication:
    def test_exact_title_duplicates_removed(self):
        papers = [
            make_paper("Deep Learning for NLP"),
            make_paper("Deep Learning for NLP"),
        ]
        unique = SearchEngine._deduplicate(papers)
        assert len(unique) == 1

    def test_case_insensitive_deduplication(self):
        papers = [
            make_paper("deep learning for nlp"),
            make_paper("Deep Learning for NLP"),
        ]
        unique = SearchEngine._deduplicate(papers)
        assert len(unique) == 1

    def test_different_titles_kept(self):
        papers = [
            make_paper("Deep Learning for NLP"),
            make_paper("Attention Is All You Need"),
        ]
        unique = SearchEngine._deduplicate(papers)
        assert len(unique) == 2

    def test_higher_citation_count_wins_on_duplicate(self):
        papers = [
            make_paper("Deep Learning for NLP", citations=5),
            make_paper("Deep Learning for NLP", citations=100),
        ]
        unique = SearchEngine._deduplicate(papers)
        assert unique[0].citation_count == 100

    def test_empty_input(self):
        assert SearchEngine._deduplicate([]) == []


class TestRanking:
    def test_sort_by_citations(self):
        papers = [
            make_paper("Paper A", citations=10),
            make_paper("Paper B", citations=500),
            make_paper("Paper C", citations=1),
        ]
        ranked = SearchEngine._rank(papers, "query", "citations")
        assert ranked[0].citation_count == 500
        assert ranked[-1].citation_count == 1

    def test_sort_by_date(self):
        papers = [
            make_paper("Paper A", year=2019),
            make_paper("Paper B", year=2023),
            make_paper("Paper C", year=2021),
        ]
        ranked = SearchEngine._rank(papers, "query", "date")
        assert ranked[0].year == 2023
        assert ranked[-1].year == 2019

    def test_relevance_sort_title_match_scores_higher(self):
        papers = [
            make_paper("Unrelated Paper about weather", citations=1000),
            make_paper("Deep Learning for healthcare", citations=1),
        ]
        ranked = SearchEngine._rank(papers, "deep learning", "relevance")
        # "Deep Learning for healthcare" should score higher due to title match
        assert "Deep Learning" in ranked[0].title

    def test_empty_papers(self):
        assert SearchEngine._rank([], "query", "relevance") == []


class TestSearchQuery:
    def test_default_sources(self):
        q = SearchQuery(query="language models")
        assert "arxiv" in q.sources
        assert "semantic_scholar" in q.sources

    def test_max_results_capped(self):
        with pytest.raises(Exception):
            SearchQuery(query="test", max_results=100)  # max is 50
