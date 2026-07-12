"""
ResearchAI — Database Layer
SQLite schema definitions and CRUD helpers using aiosqlite.
"""

from __future__ import annotations
import json
import uuid
import aiosqlite
from datetime import datetime
from typing import List, Optional, Dict, Any

from researchai.backend.core.logger import get_logger
from researchai.config import settings

logger = get_logger("database")

DB_PATH = str(settings.DB_PATH)

# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS papers (
    id              TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    authors         TEXT,          -- JSON array
    abstract        TEXT,
    year            INTEGER,
    source          TEXT,
    doi             TEXT,
    url             TEXT,
    pdf_url         TEXT,
    citation_count  INTEGER,
    keywords        TEXT,          -- JSON array
    venue           TEXT,
    local_pdf_path  TEXT,
    relevance_score REAL,
    added_at        TEXT
);

CREATE TABLE IF NOT EXISTS paper_chunks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id    TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    text        TEXT NOT NULL,
    section     TEXT,
    page_number INTEGER,
    FOREIGN KEY (paper_id) REFERENCES papers (id)
);

CREATE TABLE IF NOT EXISTS search_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    query       TEXT NOT NULL,
    sources     TEXT,              -- JSON array
    result_count INTEGER,
    searched_at TEXT
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id          TEXT PRIMARY KEY,
    paper_ids   TEXT,              -- JSON array
    messages    TEXT,              -- JSON array
    created_at  TEXT
);

CREATE TABLE IF NOT EXISTS reports (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    topic       TEXT,
    content     TEXT,              -- JSON blob
    created_at  TEXT
);

CREATE TABLE IF NOT EXISTS citations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id    TEXT NOT NULL,
    format      TEXT NOT NULL,
    citation_text TEXT NOT NULL,
    created_at  TEXT
);
"""


# ---------------------------------------------------------------------------
# Initialise DB
# ---------------------------------------------------------------------------
async def init_db() -> None:
    """Create all tables if they do not exist."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA_SQL)
        await db.commit()
    logger.info("Database initialised at %s", DB_PATH)


# ---------------------------------------------------------------------------
# Papers CRUD
# ---------------------------------------------------------------------------
async def save_paper(paper_dict: Dict[str, Any]) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO papers
            (id, title, authors, abstract, year, source, doi, url,
             pdf_url, citation_count, keywords, venue, local_pdf_path,
             relevance_score, added_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                paper_dict["id"],
                paper_dict.get("title", ""),
                json.dumps(paper_dict.get("authors", [])),
                paper_dict.get("abstract"),
                paper_dict.get("year"),
                paper_dict.get("source", ""),
                paper_dict.get("doi"),
                paper_dict.get("url"),
                paper_dict.get("pdf_url"),
                paper_dict.get("citation_count"),
                json.dumps(paper_dict.get("keywords", [])),
                paper_dict.get("venue"),
                paper_dict.get("local_pdf_path"),
                paper_dict.get("relevance_score"),
                datetime.utcnow().isoformat(),
            ),
        )
        await db.commit()


async def get_paper(paper_id: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM papers WHERE id=?", (paper_id,)) as cur:
            row = await cur.fetchone()
            if row:
                d = dict(row)
                d["authors"] = json.loads(d.get("authors") or "[]")
                d["keywords"] = json.loads(d.get("keywords") or "[]")
                return d
    return None


async def list_papers(limit: int = 100) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM papers ORDER BY added_at DESC LIMIT ?", (limit,)
        ) as cur:
            rows = await cur.fetchall()
            result = []
            for row in rows:
                d = dict(row)
                d["authors"] = json.loads(d.get("authors") or "[]")
                d["keywords"] = json.loads(d.get("keywords") or "[]")
                result.append(d)
            return result


async def save_chunks(chunks: List[Dict[str, Any]]) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executemany(
            """
            INSERT OR REPLACE INTO paper_chunks
            (paper_id, chunk_index, text, section, page_number)
            VALUES (?,?,?,?,?)
            """,
            [
                (
                    c["paper_id"],
                    c["chunk_index"],
                    c["text"],
                    c.get("section"),
                    c.get("page_number"),
                )
                for c in chunks
            ],
        )
        await db.commit()


async def get_chunks_for_paper(paper_id: str) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM paper_chunks WHERE paper_id=? ORDER BY chunk_index",
            (paper_id,),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


# ---------------------------------------------------------------------------
# Search History
# ---------------------------------------------------------------------------
async def log_search(query: str, sources: List[str], result_count: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO search_history (query, sources, result_count, searched_at) VALUES (?,?,?,?)",
            (query, json.dumps(sources), result_count, datetime.utcnow().isoformat()),
        )
        await db.commit()


async def get_search_history(limit: int = 50) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM search_history ORDER BY searched_at DESC LIMIT ?", (limit,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


# ---------------------------------------------------------------------------
# Chat Sessions
# ---------------------------------------------------------------------------
async def save_session(session_id: str, paper_ids: List[str], messages: List[Dict]) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO chat_sessions (id, paper_ids, messages, created_at) VALUES (?,?,?,?)",
            (
                session_id,
                json.dumps(paper_ids),
                json.dumps(messages),
                datetime.utcnow().isoformat(),
            ),
        )
        await db.commit()


async def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM chat_sessions WHERE id=?", (session_id,)) as cur:
            row = await cur.fetchone()
            if row:
                d = dict(row)
                d["paper_ids"] = json.loads(d.get("paper_ids") or "[]")
                d["messages"] = json.loads(d.get("messages") or "[]")
                return d
    return None


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
async def save_report(topic: str, content: Dict[str, Any]) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO reports (topic, content, created_at) VALUES (?,?,?)",
            (topic, json.dumps(content), datetime.utcnow().isoformat()),
        )
        await db.commit()
        return cursor.lastrowid


async def list_reports() -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM reports ORDER BY created_at DESC") as cur:
            rows = await cur.fetchall()
            result = []
            for row in rows:
                d = dict(row)
                d["content"] = json.loads(d.get("content") or "{}")
                result.append(d)
            return result


# ---------------------------------------------------------------------------
# Citations CRUD
# ---------------------------------------------------------------------------

async def save_citation(paper_id: str, format: str, citation_text: str) -> int:
    """Persist a generated citation. Returns the new row ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO citations (paper_id, format, citation_text, created_at) VALUES (?,?,?,?)",
            (paper_id, format, citation_text, datetime.utcnow().isoformat()),
        )
        await db.commit()
        return cursor.lastrowid


async def list_citations(format: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return all citations, optionally filtered by format."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if format:
            async with db.execute(
                "SELECT * FROM citations WHERE format=? ORDER BY created_at DESC",
                (format,),
            ) as cur:
                return [dict(r) for r in await cur.fetchall()]
        async with db.execute("SELECT * FROM citations ORDER BY created_at DESC") as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_citations_for_paper(paper_id: str) -> List[Dict[str, Any]]:
    """Return all saved citations for a specific paper."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM citations WHERE paper_id=? ORDER BY format",
            (paper_id,),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


# ---------------------------------------------------------------------------
# Paper Deletion
# ---------------------------------------------------------------------------

async def delete_paper(paper_id: str) -> bool:
    """Delete a paper and its chunks from the database. Returns True if the paper existed."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id FROM papers WHERE id=?", (paper_id,)) as cur:
            row = await cur.fetchone()
        if not row:
            return False
        await db.execute("DELETE FROM paper_chunks WHERE paper_id=?", (paper_id,))
        await db.execute("DELETE FROM citations WHERE paper_id=?", (paper_id,))
        await db.execute("DELETE FROM papers WHERE id=?", (paper_id,))
        await db.commit()
        return True
