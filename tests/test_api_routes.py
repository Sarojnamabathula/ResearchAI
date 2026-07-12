"""
Tests for the FastAPI routes using TestClient (integration tests).
These tests mock the watsonx client and DB so they run without credentials.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock


# ── Fixture: TestClient with mocked dependencies ──────────────────────────────

@pytest.fixture(scope="module")
def client():
    """
    Create a TestClient with the database and watsonx client mocked.
    This allows route tests to run without real credentials or DB.
    """
    # Mock DB init so no file is created during import
    with patch("researchai.backend.db.database.init_db", new_callable=AsyncMock):
        from researchai.backend.main import app
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


# ── Health / Info ─────────────────────────────────────────────────────────────

class TestHealthEndpoints:
    def test_health_returns_200(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"

    def test_health_has_version(self, client):
        r = client.get("/api/health")
        assert "version" in r.json()

    def test_info_lists_modules(self, client):
        r = client.get("/api/info")
        assert r.status_code == 200
        data = r.json()
        assert "modules" in data
        assert len(data["modules"]) >= 10

    def test_info_has_vector_store(self, client):
        r = client.get("/api/info")
        assert "vector_store" in r.json()


# ── OpenAPI docs ──────────────────────────────────────────────────────────────

class TestDocs:
    def test_openapi_schema_accessible(self, client):
        r = client.get("/api/openapi.json")
        assert r.status_code == 200
        schema = r.json()
        assert schema.get("info", {}).get("title") == "ResearchAI"

    def test_swagger_docs_accessible(self, client):
        r = client.get("/api/docs")
        assert r.status_code == 200


# ── Citation Format endpoint ──────────────────────────────────────────────────

class TestCitationFormatsEndpoint:
    def test_formats_endpoint_returns_list(self, client):
        r = client.get("/api/citations/formats")
        assert r.status_code == 200
        data = r.json()
        assert "formats" in data
        assert "apa" in data["formats"]
        assert "bibtex" in data["formats"]


# ── Papers endpoint (no papers stored) ───────────────────────────────────────

class TestPapersEndpoint:
    def test_list_papers_returns_200(self, client):
        with patch(
            "researchai.backend.api.routes.papers.list_papers",
            new_callable=AsyncMock,
            return_value=[],
        ):
            r = client.get("/api/papers")
            assert r.status_code == 200

    def test_get_paper_returns_404_when_missing(self, client):
        with patch(
            "researchai.backend.api.routes.papers.get_paper",
            new_callable=AsyncMock,
            return_value=None,
        ):
            r = client.get("/api/papers/doesnotexist")
            assert r.status_code == 404
