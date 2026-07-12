"""
ResearchAI — Page 8: Report Generator
Generate full structured research reports ready for export.
"""

import streamlit as st
import requests
import os
from datetime import datetime

st.set_page_config(page_title="Reports — ResearchAI", page_icon="📊", layout="wide")

API_BASE = os.getenv("RESEARCHAI_API_URL", "http://localhost:8000")

st.title("📊 Research Report Generator")
st.caption(
    "Generate comprehensive, structured research reports with literature review, "
    "comparative analysis, gap identification, and citations."
)

# ── Load Papers ───────────────────────────────────────────────────────────────
try:
    r = requests.get(f"{API_BASE}/api/papers", params={"limit": 100}, timeout=10)
    papers = r.json() if r.status_code == 200 else []
except Exception:
    papers = []

paper_map = {p["id"]: f"{p.get('title','')[:70]} ({p.get('year','?')})" for p in papers}

# ── Form ──────────────────────────────────────────────────────────────────────
st.subheader("Report Configuration")
topic = st.text_input("Report Topic", placeholder="e.g. AI in Healthcare: A Comprehensive Review")

col1, col2 = st.columns(2)
with col1:
    paper_ids = st.multiselect(
        "Papers to include (leave empty = use all)",
        options=list(paper_map.keys()),
        format_func=lambda pid: paper_map.get(pid, pid),
    )
    citation_format = st.selectbox("Citation format", ["apa", "ieee", "mla", "chicago", "bibtex"])

with col2:
    sections = st.multiselect(
        "Report sections",
        [
            "title", "abstract", "introduction", "background",
            "literature_review", "comparative_analysis",
            "research_gap", "proposed_direction", "references",
        ],
        default=[
            "title", "abstract", "introduction", "background",
            "literature_review", "comparative_analysis",
            "research_gap", "proposed_direction", "references",
        ],
    )

gen_btn = st.button("📊 Generate Report", use_container_width=True, type="primary")

if gen_btn:
    if not topic:
        st.warning("Please enter a report topic.")
        st.stop()
    with st.spinner("Generating comprehensive research report… this may take several minutes."):
        try:
            resp = requests.post(
                f"{API_BASE}/api/reports/generate",
                json={
                    "topic": topic,
                    "paper_ids": paper_ids,
                    "include_sections": sections,
                    "citation_format": citation_format,
                },
                timeout=600,
            )
            if resp.status_code == 200:
                report = resp.json()
                st.success(
                    f"Report generated — **{report.get('word_count', 0):,} words** · "
                    f"**{report.get('paper_count', 0)} papers**"
                )

                # ── Render Report ─────────────────────────────────────────
                st.markdown(f"# {report.get('title', topic)}")
                st.caption(
                    f"Generated: {report.get('generated_at','')[:19]} · "
                    f"Citations: {report.get('citation_format','').upper()}"
                )
                st.markdown("---")

                section_map = {
                    "abstract": "Abstract",
                    "introduction": "1. Introduction",
                    "background": "2. Background",
                    "literature_review": "3. Literature Review",
                    "comparative_analysis": "4. Comparative Analysis",
                    "research_gap": "5. Research Gaps",
                    "proposed_direction": "6. Proposed Research Direction",
                }

                for key, label in section_map.items():
                    val = report.get(key)
                    if val and key in sections:
                        st.subheader(label)
                        st.write(val)
                        st.markdown("---")

                if report.get("references") and "references" in sections:
                    st.subheader("References")
                    for ref in report["references"]:
                        st.markdown(f"- {ref}")

                # ── Download ──────────────────────────────────────────────
                md_parts = [f"# {report.get('title', topic)}\n"]
                for key, label in section_map.items():
                    val = report.get(key)
                    if val:
                        md_parts.append(f"\n## {label}\n{val}")
                if report.get("references"):
                    md_parts.append("\n## References")
                    for ref in report["references"]:
                        md_parts.append(f"- {ref}")

                md_text = "\n".join(md_parts)
                st.download_button(
                    "⬇️ Download Report (Markdown)",
                    data=md_text,
                    file_name=f"report_{topic[:30].replace(' ','_')}_{datetime.now().strftime('%Y%m%d')}.md",
                    mime="text/markdown",
                )
            else:
                st.error(f"Failed ({resp.status_code}): {resp.text[:400]}")
        except Exception as e:
            st.error(str(e))

# ── Previous Reports ──────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Previous Reports")
try:
    r = requests.get(f"{API_BASE}/api/reports", timeout=10)
    if r.status_code == 200:
        prev = r.json()
        if prev:
            for rep in prev[:5]:
                with st.expander(
                    f"📄 {rep.get('topic','Untitled')} — {rep.get('created_at','')[:10]}"
                ):
                    c = rep.get("content", {})
                    st.write(c.get("abstract", ""))
        else:
            st.info("No previous reports.")
except Exception:
    pass
