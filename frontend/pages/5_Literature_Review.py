"""
ResearchAI — Page 5: Literature Review Generator
Auto-generate academic literature review sections from indexed papers.
"""

import streamlit as st
import requests
import os

st.set_page_config(page_title="Literature Review — ResearchAI", page_icon="📚", layout="wide")

API_BASE = os.getenv("RESEARCHAI_API_URL", "http://localhost:8000")

st.title("📚 Literature Review")
st.caption("Generate an academic-quality literature review from your indexed papers.")

# ── Load Papers ───────────────────────────────────────────────────────────────
try:
    r = requests.get(f"{API_BASE}/api/papers", params={"limit": 100}, timeout=10)
    papers = r.json() if r.status_code == 200 else []
except Exception:
    papers = []

paper_map = {p["id"]: f"{p.get('title','')[:70]} ({p.get('year','?')})" for p in papers}

# ── Form ──────────────────────────────────────────────────────────────────────
topic = st.text_input(
    "Research Topic",
    placeholder="e.g. Large Language Models for code generation",
    help="The central theme for the literature review.",
)

use_all = st.checkbox("Use all indexed papers", value=True)
if not use_all:
    selected_ids = st.multiselect(
        "Select papers",
        options=list(paper_map.keys()),
        format_func=lambda pid: paper_map.get(pid, pid),
    )
else:
    selected_ids = []

generate = st.button("📚 Generate Literature Review", use_container_width=True, type="primary")

if generate:
    if not topic:
        st.warning("Please enter a research topic.")
        st.stop()
    with st.spinner("Generating literature review… this may take a minute."):
        try:
            resp = requests.post(
                f"{API_BASE}/api/review",
                json={
                    "topic": topic,
                    "paper_ids": selected_ids,
                    "use_all_papers": use_all,
                },
                timeout=300,
            )
            if resp.status_code == 200:
                review = resp.json()
                st.success(
                    f"Review generated from **{review.get('paper_count', 0)} papers**."
                )

                st.markdown(f"## {review.get('topic', topic)}")

                if review.get("abstract"):
                    st.subheader("Abstract")
                    st.write(review["abstract"])

                if review.get("introduction"):
                    st.subheader("1. Introduction")
                    st.write(review["introduction"])

                for i, (section_title, content) in enumerate(
                    review.get("thematic_sections", {}).items(), 2
                ):
                    st.subheader(f"{i}. {section_title}")
                    st.write(content)

                if review.get("trends"):
                    st.subheader("Research Trends")
                    for t in review["trends"]:
                        st.markdown(f"- {t}")

                cols = st.columns(2)
                with cols[0]:
                    if review.get("strengths"):
                        st.subheader("Strengths")
                        for s in review["strengths"]:
                            st.markdown(f"- ✅ {s}")
                with cols[1]:
                    if review.get("weaknesses"):
                        st.subheader("Weaknesses / Gaps")
                        for w in review["weaknesses"]:
                            st.markdown(f"- ⚠️ {w}")

                if review.get("unresolved_challenges"):
                    st.subheader("Unresolved Challenges")
                    for c in review["unresolved_challenges"]:
                        st.markdown(f"- ❓ {c}")

                if review.get("conclusion"):
                    st.subheader("Conclusion")
                    st.write(review["conclusion"])

                if review.get("references"):
                    with st.expander("References"):
                        for ref in review["references"]:
                            st.markdown(f"- {ref}")

                # ── Export ────────────────────────────────────────────────
                md_parts = [f"# Literature Review: {topic}\n"]
                for key in ["abstract", "introduction", "conclusion"]:
                    if review.get(key):
                        md_parts.append(f"\n## {key.title()}\n{review[key]}")
                for t, c in review.get("thematic_sections", {}).items():
                    md_parts.append(f"\n## {t}\n{c}")
                md_text = "\n".join(md_parts)
                st.download_button(
                    "⬇️ Download as Markdown",
                    data=md_text,
                    file_name=f"literature_review_{topic[:30].replace(' ','_')}.md",
                    mime="text/markdown",
                )
            else:
                st.error(f"Failed ({resp.status_code}): {resp.text[:400]}")
        except Exception as e:
            st.error(str(e))
