"""
ResearchAI — Page 1: Literature Search
Search arXiv, Semantic Scholar, and CrossRef with query analysis.
"""

import streamlit as st
import requests
import os

st.set_page_config(page_title="Search — ResearchAI", page_icon="🔍", layout="wide")

API_BASE = os.getenv("RESEARCHAI_API_URL", "http://localhost:8000")

st.title("🔍 Literature Search")
st.caption("Search across arXiv, Semantic Scholar, and CrossRef simultaneously.")

# ── Search Form ──────────────────────────────────────────────────────────────
with st.form("search_form"):
    query = st.text_input(
        "Research Query",
        placeholder="e.g. Federated Learning for healthcare data privacy",
        help="Enter a natural language research question or topic.",
    )
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    with col1:
        sources = st.multiselect(
            "Sources",
            ["arxiv", "semantic_scholar", "crossref"],
            default=["arxiv", "semantic_scholar", "crossref"],
        )
    with col2:
        max_results = st.number_input("Max results", min_value=5, max_value=50, value=10)
    with col3:
        year_from = st.number_input("Year from", min_value=1990, max_value=2025, value=2018)
    with col4:
        sort_by = st.selectbox("Sort by", ["relevance", "date", "citations"])

    submitted = st.form_submit_button("🔍 Search", use_container_width=True)

# ── Query Analysis Expander ───────────────────────────────────────────────────
if query:
    with st.expander("🧠 Query Analysis", expanded=False):
        with st.spinner("Analysing query…"):
            try:
                r = requests.get(
                    f"{API_BASE}/api/search/analyze",
                    params={"q": query},
                    timeout=30,
                )
                if r.status_code == 200:
                    a = r.json()
                    col1, col2 = st.columns(2)
                    col1.markdown(f"**Topic:** {a.get('topic', '-')}")
                    col1.markdown(f"**Domain:** {a.get('domain', '-')}")
                    col1.markdown(f"**Intent:** {a.get('intent', '-')}")
                    col2.markdown(f"**Keywords:** {', '.join(a.get('keywords', []))}")
                    col2.markdown(f"**Related:** {', '.join(a.get('related_concepts', []))}")
                    if a.get("search_expansions"):
                        st.markdown("**Search expansions:**")
                        for exp in a["search_expansions"]:
                            st.markdown(f"  - {exp}")
            except Exception as e:
                st.warning(f"Query analysis unavailable: {e}")

# ── Execute Search ────────────────────────────────────────────────────────────
if submitted and query:
    with st.spinner(f"Searching {len(sources)} sources…"):
        payload = {
            "query": query,
            "sources": sources,
            "max_results": max_results,
            "year_from": year_from,
            "year_to": 2025,
            "sort_by": sort_by,
        }
        try:
            r = requests.post(f"{API_BASE}/api/search", json=payload, timeout=60)
            if r.status_code == 200:
                result = r.json()
                papers = result.get("papers", [])
                st.success(
                    f"Found **{result.get('total_found', 0)} papers** "
                    f"in **{result.get('search_time_ms', 0):.0f} ms** "
                    f"from {', '.join(result.get('sources_queried', []))}"
                )
                if result.get("keywords_extracted"):
                    st.info(f"Extracted keywords: {', '.join(result['keywords_extracted'])}")

                st.markdown("---")
                for i, paper in enumerate(papers):
                    authors = paper.get("authors", [])
                    author_str = ", ".join(
                        a.get("name", "") if isinstance(a, dict) else str(a)
                        for a in authors[:3]
                    )
                    if len(authors) > 3:
                        author_str += f" +{len(authors)-3} more"

                    with st.container(border=True):
                        col_title, col_score = st.columns([5, 1])
                        with col_title:
                            st.markdown(f"### {i+1}. {paper.get('title', 'No title')}")
                        with col_score:
                            score = paper.get("relevance_score", 0)
                            st.metric("Relevance", f"{score:.2f}")

                        meta_col1, meta_col2, meta_col3, meta_col4 = st.columns(4)
                        meta_col1.markdown(f"**Authors:** {author_str or 'Unknown'}")
                        meta_col2.markdown(f"**Year:** {paper.get('year', 'N/A')}")
                        meta_col3.markdown(f"**Source:** {paper.get('source', 'N/A')}")
                        meta_col4.markdown(f"**Citations:** {paper.get('citation_count', 'N/A')}")

                        if paper.get("abstract"):
                            with st.expander("Abstract"):
                                st.write(paper["abstract"])

                        btn_col1, btn_col2, btn_col3 = st.columns(3)
                        paper_id = paper.get("id", "")

                        if paper.get("pdf_url") and btn_col1.button(
                            "📥 Process PDF", key=f"proc_{paper_id}"
                        ):
                            with st.spinner("Downloading and indexing PDF…"):
                                resp = requests.post(
                                    f"{API_BASE}/api/papers/process",
                                    json={"paper_id": paper_id, "pdf_url": paper["pdf_url"]},
                                    timeout=120,
                                )
                                if resp.status_code == 200:
                                    d = resp.json()
                                    st.success(
                                        f"Indexed {d.get('chunks')} chunks "
                                        f"from {d.get('pages')} pages."
                                    )
                                else:
                                    st.error(f"Processing failed: {resp.text[:300]}")

                        if paper.get("pdf_url"):
                            btn_col2.markdown(
                                f"[📄 View PDF]({paper['pdf_url']})", unsafe_allow_html=True
                            )
                        if paper.get("doi"):
                            btn_col3.markdown(
                                f"[🔗 DOI](https://doi.org/{paper['doi']})",
                                unsafe_allow_html=True,
                            )
            else:
                st.error(f"Search failed ({r.status_code}): {r.text[:400]}")
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to backend. Make sure it's running: `python run.py`")
        except Exception as e:
            st.error(f"Unexpected error: {e}")

# ── Search History ────────────────────────────────────────────────────────────
with st.expander("📜 Recent Searches"):
    try:
        r = requests.get(f"{API_BASE}/api/search/history", params={"limit": 10}, timeout=5)
        if r.status_code == 200:
            history = r.json()
            if history:
                for h in history:
                    st.markdown(
                        f"- **{h.get('query', '')}** — "
                        f"{h.get('result_count', 0)} results · "
                        f"{h.get('searched_at', '')[:19]}"
                    )
            else:
                st.info("No searches yet.")
    except Exception:
        st.info("Search history unavailable.")
