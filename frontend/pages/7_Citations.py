"""
ResearchAI — Page 7: Citation Manager
Generate and export citations in APA, IEEE, MLA, Chicago, and BibTeX.
"""

import streamlit as st
import requests
import os

st.set_page_config(page_title="Citations — ResearchAI", page_icon="📜", layout="wide")

API_BASE = os.getenv("RESEARCHAI_API_URL", "http://localhost:8000")

st.title("📜 Citation Manager")
st.caption("Generate citations in multiple formats. Never fabricate references.")

# ── Load Papers ───────────────────────────────────────────────────────────────
try:
    r = requests.get(f"{API_BASE}/api/papers", params={"limit": 100}, timeout=10)
    papers = r.json() if r.status_code == 200 else []
except Exception:
    papers = []

if not papers:
    st.info("No papers found. Search and index papers first.")
    st.stop()

paper_map = {p["id"]: f"{p.get('title','')[:70]} ({p.get('year','?')})" for p in papers}

# ── Supported Formats ─────────────────────────────────────────────────────────
try:
    fr = requests.get(f"{API_BASE}/api/citations/formats", timeout=5)
    formats = fr.json().get("formats", ["apa", "ieee", "mla", "chicago", "bibtex"])
except Exception:
    formats = ["apa", "ieee", "mla", "chicago", "bibtex"]

# ── Form ──────────────────────────────────────────────────────────────────────
col1, col2 = st.columns([3, 1])
with col1:
    selected_ids = st.multiselect(
        "Select papers to cite",
        options=list(paper_map.keys()),
        format_func=lambda pid: paper_map.get(pid, pid),
        default=list(paper_map.keys()),
    )
with col2:
    fmt = st.selectbox("Citation format", options=formats, index=0)

gen_btn = st.button("📜 Generate Citations", use_container_width=True, type="primary")

if gen_btn:
    if not selected_ids:
        st.warning("Select at least one paper.")
        st.stop()
    with st.spinner(f"Generating {fmt.upper()} citations…"):
        try:
            resp = requests.post(
                f"{API_BASE}/api/citations/generate",
                json={"paper_ids": selected_ids, "format": fmt},
                timeout=60,
            )
            if resp.status_code == 200:
                result = resp.json()
                citations = result.get("citations", [])
                formatted_refs = result.get("formatted_references", "")

                st.success(f"Generated **{len(citations)}** {fmt.upper()} citations.")

                # Individual citations
                for c in citations:
                    with st.container(border=True):
                        st.markdown(f"**Paper ID:** `{c.get('paper_id', '')}`")
                        if fmt == "bibtex":
                            st.code(c.get("citation_text", ""), language="bibtex")
                        else:
                            st.write(c.get("citation_text", ""))
                        if c.get("bibtex_key"):
                            st.caption(f"BibTeX key: `{c['bibtex_key']}`")

                # Full reference list
                if formatted_refs:
                    st.subheader("Full Reference List")
                    if fmt == "bibtex":
                        st.code(formatted_refs, language="bibtex")
                    else:
                        st.text_area("References", value=formatted_refs, height=300)

                # Download
                ext = "bib" if fmt == "bibtex" else "txt"
                st.download_button(
                    f"⬇️ Download as .{ext}",
                    data=formatted_refs,
                    file_name=f"references_{fmt}.{ext}",
                    mime="text/plain",
                )
            else:
                st.error(f"Failed ({resp.status_code}): {resp.text[:400]}")
        except Exception as e:
            st.error(str(e))

# ── Format Guide ──────────────────────────────────────────────────────────────
with st.expander("ℹ️ Citation Format Guide"):
    st.markdown(
        """
| Format | Style | Common Use |
|--------|-------|------------|
| APA | Author, A. (Year). Title. *Venue*. | Social sciences, education |
| IEEE | A. Author, "Title," *Venue*, Year. | Engineering, CS |
| MLA | Author. "Title." *Venue* Year. | Humanities |
| Chicago | Author. "Title." *Venue* Year. | History, arts |
| BibTeX | @article{key, ...} | LaTeX documents |
        """
    )
