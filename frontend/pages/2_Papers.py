"""
ResearchAI — Page 2: Paper Viewer & Summarization
Browse indexed papers, view details, generate summaries.
"""

import streamlit as st
import requests
import os

st.set_page_config(page_title="Papers — ResearchAI", page_icon="📄", layout="wide")

API_BASE = os.getenv("RESEARCHAI_API_URL", "http://localhost:8000")

st.title("📄 Paper Viewer")
st.caption("Browse, inspect, and summarize your indexed research papers.")

# ── Upload Panel ──────────────────────────────────────────────────────────────
with st.expander("⬆️ Upload a PDF"):
    uploaded = st.file_uploader("Choose a PDF file", type=["pdf"])
    if uploaded and st.button("Upload & Index", key="upload_btn"):
        with st.spinner("Processing PDF…"):
            try:
                resp = requests.post(
                    f"{API_BASE}/api/papers/upload",
                    files={"file": (uploaded.name, uploaded.getvalue(), "application/pdf")},
                    timeout=120,
                )
                if resp.status_code == 200:
                    d = resp.json()
                    st.success(
                        f"Uploaded **{d.get('filename')}** — "
                        f"{d.get('chunks')} chunks from {d.get('pages')} pages. "
                        f"Paper ID: `{d.get('paper_id')}`"
                    )
                else:
                    st.error(f"Upload failed: {resp.text[:400]}")
            except Exception as e:
                st.error(str(e))

st.markdown("---")

# ── Load Papers ───────────────────────────────────────────────────────────────
try:
    r = requests.get(f"{API_BASE}/api/papers", params={"limit": 100}, timeout=10)
    papers = r.json() if r.status_code == 200 else []
except Exception:
    papers = []

if not papers:
    st.info("No papers indexed yet. Use the Search page to find papers and process their PDFs.")
    st.stop()

# Build a lookup by paper ID for the selector
paper_map = {p.get("id"): p for p in papers}
paper_titles = {
    p.get("id"): f"{p.get('title', 'Untitled')[:80]} ({p.get('year', '?')})"
    for p in papers
}

st.metric("Indexed Papers", len(papers))

# ── Paper Selector ────────────────────────────────────────────────────────────
selected_id = st.selectbox(
    "Select paper",
    options=list(paper_titles.keys()),
    format_func=lambda pid: paper_titles.get(pid, pid),
)

if not selected_id:
    st.stop()

paper = paper_map[selected_id]

# ── Paper Header ──────────────────────────────────────────────────────────────
st.markdown(f"## {paper.get('title', 'Untitled')}")

authors = paper.get("authors", [])
author_str = ", ".join(
    a.get("name", "") if isinstance(a, dict) else str(a) for a in authors[:5]
)
st.caption(f"**Authors:** {author_str or 'Unknown'} · **Year:** {paper.get('year', '?')} · **Source:** {paper.get('source', '?')}")

col1, col2, col3 = st.columns(3)
col1.metric("Citations", paper.get("citation_count", "N/A"))
col2.metric("Venue", paper.get("venue") or "—")
col3.metric("Relevance", f"{paper.get('relevance_score', 0):.2f}" if paper.get("relevance_score") else "—")

if paper.get("abstract"):
    st.subheader("Abstract")
    st.write(paper["abstract"])

link_col1, link_col2, link_col3 = st.columns(3)
if paper.get("pdf_url"):
    link_col1.markdown(f"[📄 PDF]({paper['pdf_url']})")
if paper.get("doi"):
    link_col2.markdown(f"[🔗 DOI](https://doi.org/{paper['doi']})")

# ── Delete Button ─────────────────────────────────────────────────────────────
if link_col3.button("🗑️ Delete Paper", type="secondary"):
    r = requests.delete(f"{API_BASE}/api/papers/{selected_id}", timeout=10)
    if r.status_code == 200:
        st.success("Paper deleted.")
        st.rerun()
    else:
        st.error(f"Delete failed: {r.text[:200]}")

st.markdown("---")

# ── Summarization ─────────────────────────────────────────────────────────────
st.subheader("📝 Generate Summary")
sum_col1, sum_col2 = st.columns([2, 1])
with sum_col1:
    level = st.radio("Summary level", ["short", "medium", "detailed"], horizontal=True)
with sum_col2:
    gen_sum = st.button("Generate Summary", use_container_width=True)

if gen_sum:
    with st.spinner(f"Generating {level} summary…"):
        try:
            resp = requests.post(
                f"{API_BASE}/api/summarize",
                json={"paper_id": selected_id, "level": level},
                timeout=120,
            )
            if resp.status_code == 200:
                s = resp.json()
                st.success(f"Confidence: **{s.get('confidence', 0):.0%}**")
                if level == "short":
                    st.markdown(s.get("short_summary", ""))
                else:
                    for field in ["problem_statement", "objective", "methodology",
                                  "dataset", "algorithms", "results",
                                  "contributions", "limitations", "future_work"]:
                        val = s.get(field)
                        if val:
                            st.markdown(f"**{field.replace('_', ' ').title()}:** {val}")
            else:
                st.error(f"Summarization failed: {resp.text[:400]}")
        except Exception as e:
            st.error(str(e))

# ── Chunks Preview ────────────────────────────────────────────────────────────
with st.expander("🔍 View Text Chunks"):
    try:
        r = requests.get(f"{API_BASE}/api/papers/{selected_id}/chunks", timeout=10)
        if r.status_code == 200:
            chunks = r.json()
            st.caption(f"{len(chunks)} chunks indexed")
            for c in chunks[:10]:
                st.markdown(
                    f"**Chunk {c.get('chunk_index')}** "
                    f"({c.get('section', 'general')}) — "
                    f"page {c.get('page_number', '?')}"
                )
                st.text(c.get("text", "")[:300] + "…")
                st.markdown("---")
            if len(chunks) > 10:
                st.caption(f"… {len(chunks)-10} more chunks not shown")
        else:
            st.info("No chunks indexed. Process the PDF first.")
    except Exception as e:
        st.warning(str(e))
