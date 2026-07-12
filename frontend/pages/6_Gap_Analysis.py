"""
ResearchAI — Page 6: Gap Analysis & Hypothesis Generator
Identify research gaps and generate novel hypotheses.
"""

import streamlit as st
import requests
import os

st.set_page_config(page_title="Gap Analysis — ResearchAI", page_icon="🔎", layout="wide")

API_BASE = os.getenv("RESEARCHAI_API_URL", "http://localhost:8000")

st.title("🔎 Research Gap Analysis")
st.caption(
    "Automatically identify underexplored topics, missing datasets, "
    "weak methodologies, and contradictory findings."
)

# ── Load Papers ───────────────────────────────────────────────────────────────
try:
    r = requests.get(f"{API_BASE}/api/papers", params={"limit": 100}, timeout=10)
    papers = r.json() if r.status_code == 200 else []
except Exception:
    papers = []

paper_map = {p["id"]: f"{p.get('title','')[:70]} ({p.get('year','?')})" for p in papers}

topic = st.text_input("Research Topic", placeholder="e.g. Transformer models in NLP")
use_all = st.checkbox("Use all indexed papers", value=True)
if not use_all:
    selected_ids = st.multiselect(
        "Select papers",
        options=list(paper_map.keys()),
        format_func=lambda pid: paper_map.get(pid, pid),
    )
else:
    selected_ids = []

col1, col2 = st.columns(2)
run_gaps = col1.button("🔎 Identify Research Gaps", use_container_width=True, type="primary")
run_hypo = col2.button("💡 Generate Hypotheses", use_container_width=True)

# ── Gap Analysis ──────────────────────────────────────────────────────────────
if run_gaps:
    if not topic:
        st.warning("Please enter a research topic.")
        st.stop()
    with st.spinner("Analysing literature for research gaps…"):
        try:
            resp = requests.post(
                f"{API_BASE}/api/gaps/analyze",
                json={"topic": topic, "paper_ids": selected_ids, "use_all_papers": use_all},
                timeout=300,
            )
            if resp.status_code == 200:
                result = resp.json()
                st.success(
                    f"Analysed **{result.get('paper_count_analyzed', 0)} papers** — "
                    f"found **{len(result.get('gaps', []))} gaps**."
                )

                if result.get("summary"):
                    st.subheader("Summary")
                    st.write(result["summary"])

                gap_type_icons = {
                    "underexplored_topic": "🔍",
                    "missing_dataset": "🗄️",
                    "weak_methodology": "⚙️",
                    "contradictory_findings": "⚡",
                    "future_opportunity": "🚀",
                }

                for gap in result.get("gaps", []):
                    icon = gap_type_icons.get(gap.get("gap_type", ""), "•")
                    with st.container(border=True):
                        g_col1, g_col2 = st.columns([4, 1])
                        g_col1.markdown(f"### {icon} {gap.get('title', 'Gap')}")
                        g_col2.metric("Confidence", f"{gap.get('confidence', 0):.0%}")
                        st.caption(f"Type: **{gap.get('gap_type','').replace('_',' ').title()}**")
                        st.write(gap.get("description", ""))
                        st.markdown(f"**Why it matters:** {gap.get('importance', '')}")
                        if gap.get("supporting_papers"):
                            st.caption(
                                f"Supporting papers: {', '.join(gap['supporting_papers'])}"
                            )
            else:
                st.error(f"Failed ({resp.status_code}): {resp.text[:400]}")
        except Exception as e:
            st.error(str(e))

# ── Hypothesis Generator ──────────────────────────────────────────────────────
if run_hypo:
    if not topic:
        st.warning("Please enter a research topic.")
        st.stop()
    with st.spinner("Generating novel research hypotheses…"):
        try:
            resp = requests.post(
                f"{API_BASE}/api/gaps/hypotheses",
                json={"topic": topic, "paper_ids": selected_ids, "use_all_papers": use_all},
                timeout=300,
            )
            if resp.status_code == 200:
                result = resp.json()
                st.info(
                    "⚠️ The following are AI-generated research hypotheses. "
                    "They are suggestions only and require expert validation."
                )

                for h in result.get("hypotheses", []):
                    with st.container(border=True):
                        h_col1, h_col2 = st.columns([4, 1])
                        h_col1.markdown(f"### 💡 {h.get('statement', 'Hypothesis')}")
                        h_col2.metric("Confidence", f"{h.get('confidence', 0):.0%}")

                        col_a, col_b = st.columns(2)
                        col_a.markdown(f"**Motivation:** {h.get('motivation','')}")
                        col_b.markdown(f"**Novelty:** {h.get('novelty','')}")

                        st.markdown(
                            f"**Expected Contribution:** {h.get('expected_contribution','')}"
                        )

                        if h.get("evaluation_methods"):
                            st.markdown(
                                "**Evaluation methods:** "
                                + ", ".join(h["evaluation_methods"])
                            )
                        if h.get("supporting_evidence"):
                            with st.expander("Supporting Evidence"):
                                for ev in h["supporting_evidence"]:
                                    st.markdown(f"- {ev}")
            else:
                st.error(f"Failed ({resp.status_code}): {resp.text[:400]}")
        except Exception as e:
            st.error(str(e))
