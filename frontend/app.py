"""
ResearchAI — Streamlit Frontend Entry Point
Main home page and shared state/utilities.
"""

import streamlit as st

# ── Page config (must be first Streamlit call) ───────────────────────────────
st.set_page_config(
    page_title="ResearchAI — IBM watsonx",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Shared API base URL ──────────────────────────────────────────────────────
import os
API_BASE = os.getenv("RESEARCHAI_API_URL", "http://localhost:8000")

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* Sidebar nav styling */
    [data-testid="stSidebarNav"] { font-size: 0.95rem; }
    /* Metric cards */
    [data-testid="metric-container"] {
        background: #f7f8fa;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 12px 16px;
    }
    /* Primary button */
    .stButton>button {
        background-color: #3b82d4;
        color: white;
        border: none;
        border-radius: 6px;
    }
    .stButton>button:hover { background-color: #2563b0; }
    /* Code blocks */
    .stCodeBlock { font-size: 0.85rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Home page content ────────────────────────────────────────────────────────
st.title("🔬 ResearchAI")
st.caption("Intelligent Academic Research Agent powered by IBM watsonx · Granite Models")

st.markdown("---")

col1, col2, col3 = st.columns(3)
col1.metric("AI Engine", "IBM Granite")
col2.metric("Vector Store", "ChromaDB / FAISS")
col3.metric("Search Sources", "arXiv · S2 · CrossRef")

st.markdown("---")

st.subheader("What can ResearchAI do?")

features = {
    "🔍 Literature Search": "Search arXiv, Semantic Scholar, and CrossRef simultaneously.",
    "📄 PDF Processing": "Download and index research PDFs into a semantic vector store.",
    "💬 Research Chat": "Ask questions over your collected papers with full RAG support.",
    "📝 Summarization": "Get short, medium, or detailed structured summaries of any paper.",
    "⚖️ Paper Comparison": "Generate side-by-side comparison tables for multiple papers.",
    "📚 Literature Review": "Auto-generate academic-quality literature review sections.",
    "🔎 Gap Analysis": "Identify research gaps and generate novel hypotheses.",
    "📜 Citation Manager": "Export citations in APA, IEEE, MLA, Chicago, or BibTeX.",
    "📊 Reports": "Generate full structured research reports ready for export.",
    "📅 Research Timeline": "Visualize the chronological evolution of a research field.",
    "📈 Trend Analysis": "Explore publication trends, top keywords, and active authors.",
    "🧠 Explainable AI": "Every answer includes sources, confidence, and reasoning.",
}

cols = st.columns(2)
for i, (title, desc) in enumerate(features.items()):
    with cols[i % 2]:
        st.info(f"**{title}**\n\n{desc}")

st.markdown("---")
st.subheader("Quick Start")
st.markdown(
    """
1. Navigate to **Search** in the sidebar to find research papers.
2. Click **Process PDF** on any result to index it for RAG.
3. Use **Paper Chat** to ask questions over your indexed papers.
4. Use **Compare**, **Literature Review**, or **Reports** for deeper analysis.
5. Export **Citations** in your preferred format.
"""
)

# ── API health check ─────────────────────────────────────────────────────────
import requests

with st.sidebar:
    st.markdown("---")
    st.caption("API Status")
    try:
        r = requests.get(f"{API_BASE}/api/health", timeout=3)
        if r.status_code == 200:
            data = r.json()
            st.success("Backend ✅ online")
            if data.get("watsonx_configured"):
                st.success("watsonx ✅ configured")
            else:
                st.warning("watsonx ⚠️ not configured\nSet credentials in .env")
        else:
            st.error("Backend ❌ error")
    except Exception:
        st.error("Backend ❌ offline\nStart with: python run.py")
    st.caption(f"API: `{API_BASE}`")
