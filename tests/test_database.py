"""
Tests for database CRUD helpers (using a temporary SQLite database).
"""

import pytest
import asyncio
import tempfile
import os


# ── Create a temp DB file for the entire test session ────────────────────────
_tmp_db_fd, _TMP_DB_PATH = tempfile.mkstemp(suffix=".db")
os.close(_tmp_db_fd)


@pytest.fixture(scope="module", autouse=True)
def patch_db_module():
    """Point the database module at the temp DB path for all tests."""
    from researchai.backend.db import database
    original = database.DB_PATH
    database.DB_PATH = _TMP_DB_PATH
    yield
    database.DB_PATH = original
    try:
        os.unlink(_TMP_DB_PATH)
    except OSError:
        pass


@pytest.fixture(scope="module", autouse=True)
def init_database(patch_db_module):
    """Initialise the test database once for all tests in this module."""
    from researchai.backend.db import database
    asyncio.get_event_loop().run_until_complete(database.init_db())


def get_db():
    from researchai.backend.db import database
    return database


# ── Paper CRUD ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_save_and_get_paper():
    db = get_db()
    paper = {
        "id": "test:001",
        "title": "Test Paper",
        "authors": [{"name": "Test Author"}],
        "abstract": "An abstract.",
        "year": 2023,
        "source": "arxiv",
        "doi": None,
        "url": None,
        "pdf_url": None,
        "citation_count": 10,
        "keywords": ["test"],
        "venue": "TestConf",
        "local_pdf_path": None,
        "relevance_score": 0.8,
    }
    await db.save_paper(paper)
    fetched = await db.get_paper("test:001")
    assert fetched is not None
    assert fetched["title"] == "Test Paper"
    assert fetched["year"] == 2023
    assert isinstance(fetched["authors"], list)


@pytest.mark.asyncio
async def test_get_paper_returns_none_for_missing():
    db = get_db()
    result = await db.get_paper("nonexistent:999")
    assert result is None


@pytest.mark.asyncio
async def test_list_papers_returns_saved():
    db = get_db()
    papers = await db.list_papers(limit=50)
    ids = [p["id"] for p in papers]
    assert "test:001" in ids


@pytest.mark.asyncio
async def test_save_and_get_chunks():
    db = get_db()
    chunks = [
        {"paper_id": "test:001", "chunk_index": 0, "text": "First chunk",
         "section": "intro", "page_number": 1},
        {"paper_id": "test:001", "chunk_index": 1, "text": "Second chunk",
         "section": "method", "page_number": 2},
    ]
    await db.save_chunks(chunks)
    fetched = await db.get_chunks_for_paper("test:001")
    assert len(fetched) == 2
    assert fetched[0]["text"] == "First chunk"


@pytest.mark.asyncio
async def test_log_and_get_search_history():
    db = get_db()
    await db.log_search("large language models", ["arxiv", "semantic_scholar"], 15)
    history = await db.get_search_history(limit=10)
    assert len(history) >= 1
    assert any(h["query"] == "large language models" for h in history)


@pytest.mark.asyncio
async def test_save_and_get_chat_session():
    db = get_db()
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
    ]
    await db.save_session("session-001", ["test:001"], messages)
    session = await db.get_session("session-001")
    assert session is not None
    assert session["paper_ids"] == ["test:001"]
    assert len(session["messages"]) == 2


@pytest.mark.asyncio
async def test_get_session_returns_none_for_missing():
    db = get_db()
    result = await db.get_session("no-such-session")
    assert result is None


@pytest.mark.asyncio
async def test_save_and_list_reports():
    db = get_db()
    report_id = await db.save_report(
        "AI in Healthcare",
        {"title": "Report", "abstract": "Summary..."},
    )
    assert isinstance(report_id, int)
    reports = await db.list_reports()
    assert len(reports) >= 1
    assert any(r.get("topic") == "AI in Healthcare" for r in reports)


# ── Citation CRUD ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_save_and_list_citations():
    db = get_db()
    cit_id = await db.save_citation(
        "test:001", "apa", "Author, A. (2023). Test Paper. TestConf."
    )
    assert isinstance(cit_id, int)
    citations = await db.list_citations()
    assert len(citations) >= 1
    assert any(c["paper_id"] == "test:001" for c in citations)


@pytest.mark.asyncio
async def test_list_citations_filter_by_format():
    db = get_db()
    await db.save_citation("test:001", "ieee", "A. Author, 'Test Paper,' TestConf, 2023.")
    ieee_cits = await db.list_citations(format="ieee")
    assert all(c["format"] == "ieee" for c in ieee_cits)


@pytest.mark.asyncio
async def test_get_citations_for_paper():
    db = get_db()
    cits = await db.get_citations_for_paper("test:001")
    assert len(cits) >= 1
    assert all(c["paper_id"] == "test:001" for c in cits)


# ── Paper Deletion ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_paper_removes_paper_and_chunks():
    db = get_db()
    await db.save_paper({
        "id": "test:del",
        "title": "Delete Me",
        "authors": [],
        "abstract": None,
        "year": 2020,
        "source": "arxiv",
        "doi": None,
        "url": None,
        "pdf_url": None,
        "citation_count": 0,
        "keywords": [],
        "venue": None,
        "local_pdf_path": None,
        "relevance_score": 0,
    })
    await db.save_chunks([
        {"paper_id": "test:del", "chunk_index": 0, "text": "chunk",
         "section": None, "page_number": None},
    ])
    deleted = await db.delete_paper("test:del")
    assert deleted is True
    assert await db.get_paper("test:del") is None
    chunks = await db.get_chunks_for_paper("test:del")
    assert len(chunks) == 0


@pytest.mark.asyncio
async def test_delete_nonexistent_paper_returns_false():
    db = get_db()
    deleted = await db.delete_paper("never:existed")
    assert deleted is False
