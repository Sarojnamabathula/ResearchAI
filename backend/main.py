"""
ResearchAI — FastAPI Application Entry Point
Sets up middleware, startup/shutdown, exception handling, and all routers.
"""

from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from researchai.backend.core.logger import get_logger
from researchai.backend.core.exceptions import (
    ResearchAIError, ValidationError, SearchError,
    WatsonxError, PDFProcessingError, VectorStoreError,
)
from researchai.backend.db.database import init_db
from researchai.config import settings

from researchai.backend.api.routes import (
    search, papers, summarize, compare, review,
    gaps, citations, reports, chat, timeline, trends,
)

logger = get_logger("main")


# ---------------------------------------------------------------------------
# Application Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise database and shared resources on startup."""
    logger.info("ResearchAI starting up — version %s", settings.APP_VERSION)
    await init_db()
    logger.info("Database ready")
    yield
    logger.info("ResearchAI shutting down")


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Exception Handlers
# ---------------------------------------------------------------------------

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(status_code=422, content={"error": "Validation Error", "detail": str(exc)})


@app.exception_handler(SearchError)
async def search_exception_handler(request: Request, exc: SearchError):
    return JSONResponse(status_code=503, content={"error": "Search Error", "detail": str(exc)})


@app.exception_handler(WatsonxError)
async def watsonx_exception_handler(request: Request, exc: WatsonxError):
    return JSONResponse(status_code=503, content={"error": "AI Generation Error", "detail": str(exc)})


@app.exception_handler(PDFProcessingError)
async def pdf_exception_handler(request: Request, exc: PDFProcessingError):
    return JSONResponse(status_code=422, content={"error": "PDF Processing Error", "detail": str(exc)})


@app.exception_handler(VectorStoreError)
async def vector_store_exception_handler(request: Request, exc: VectorStoreError):
    return JSONResponse(status_code=503, content={"error": "Vector Store Error", "detail": str(exc)})


@app.exception_handler(ResearchAIError)
async def generic_exception_handler(request: Request, exc: ResearchAIError):
    return JSONResponse(status_code=500, content={"error": "Internal Error", "detail": str(exc)})


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@app.get("/api/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "watsonx_configured": bool(settings.WATSONX_API_KEY and settings.WATSONX_PROJECT_ID),
    }


@app.get("/api/info", tags=["System"])
async def app_info():
    """Application info and feature flags."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": settings.APP_DESCRIPTION,
        "vector_store": settings.VECTOR_STORE_TYPE,
        "model": settings.GRANITE_MODEL_ID,
        "modules": [
            "query_analysis", "literature_search", "pdf_processing",
            "knowledge_base", "rag", "summarization", "comparison",
            "literature_review", "gap_analysis", "hypothesis",
            "citation", "report", "chat", "timeline", "trends",
        ],
    }


# ---------------------------------------------------------------------------
# Register Routers
# ---------------------------------------------------------------------------

app.include_router(search.router,     prefix="/api/search",      tags=["Search"])
app.include_router(papers.router,     prefix="/api/papers",      tags=["Papers"])
app.include_router(summarize.router,  prefix="/api/summarize",   tags=["Summarization"])
app.include_router(compare.router,    prefix="/api/compare",     tags=["Comparison"])
app.include_router(review.router,     prefix="/api/review",      tags=["Literature Review"])
app.include_router(gaps.router,       prefix="/api/gaps",        tags=["Gap Analysis"])
app.include_router(citations.router,  prefix="/api/citations",   tags=["Citations"])
app.include_router(reports.router,    prefix="/api/reports",     tags=["Reports"])
app.include_router(chat.router,       prefix="/api/chat",        tags=["Chat"])
app.include_router(timeline.router,   prefix="/api/timeline",    tags=["Timeline"])
app.include_router(trends.router,     prefix="/api/trends",      tags=["Trends"])
