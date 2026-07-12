"""
ResearchAI — Page 4: Paper Comparison
Side-by-side comparison of multiple research papers.
"""

import streamlit as st
import requests
import os
import pandas as pd

st.set_page_config(page_title="Compare — ResearchAI", page_icon="⚖️", layout="wide")

API_BASE = os.getenv("RESEARCHAI_API_URL", "http://localhost:8000")

st.title("⚖️ Paper Comparison")
st.caption("Compare 2–10 papers side-by-side across method, dataset, results, and more.")

# ── Load Papers ───────────────────────────────────────────────────────────────
try:
    r = requests.get(f"{API_BASE}/api/papers", params={"limit": 100}, timeout=10)
    papers = r.json() if r.status_code == 200 else []
except Exception:
    papers = []

if len(papers) < 2:
    st.warning("You need at least 2 papers indexed. Go to Search and process some PDFs first.")
    st.stop()

paper_map = {p["id"]: f"{p.get('title','')[:70]} ({p.get('year','?')})" for p in papers}

selected_ids = st.multiselect(
    "Select papers to compare (2–10)",
    options=list(paper_map.keys()),
    format_func=lambda pid: paper_map.get(pid, pid),
    max_selections=10,
)

aspects = st.multiselect(
    "Comparison aspects",
    ["method", "dataset", "results", "limitations", "contributions", "accuracy", "metrics"],
    default=["method", "dataset", "results", "limitations", "contributions"],
)

if len(selected_ids) < 2:
    st.info("Select at least 2 papers to compare.")
    st.stop()

if st.button("⚖️ Compare Papers", use_container_width=True, type="primary"):
    with st.spinner(f"Comparing {len(selected_ids)} papers…"):
        try:
            resp = requests.post(
                f"{API_BASE}/api/compare",
                json={"paper_ids": selected_ids, "aspects": aspects},
                timeout=180,
            )
            if resp.status_code == 200:
                result = resp.json()

                # ── Comparison Table ──────────────────────────────────────
                st.subheader("Comparison Table")
                rows = result.get("papers", [])
                if rows:
                    df_data = []
                    for row in rows:
                        entry = {
                            "Title": row.get("title", "")[:60],
                            "Year": row.get("year", ""),
                            "Authors": row.get("authors", "")[:40],
                        }
                        for a in aspects:
                            entry[a.title()] = row.get(a, "—") or "—"
                        df_data.append(entry)

                    df = pd.DataFrame(df_data)
                    st.dataframe(df, use_container_width=True)

                # ── Narrative ─────────────────────────────────────────────
                if result.get("narrative_comparison"):
                    st.subheader("Narrative Comparison")
                    st.write(result["narrative_comparison"])

                # ── Key Differences & Common Ground ───────────────────────
                col1, col2 = st.columns(2)
                with col1:
                    if result.get("key_differences"):
                        st.subheader("Key Differences")
                        for d in result["key_differences"]:
                            st.markdown(f"- {d}")
                with col2:
                    if result.get("common_ground"):
                        st.subheader("Common Ground")
                        for c in result["common_ground"]:
                            st.markdown(f"- {c}")

                if result.get("recommendation"):
                    st.subheader("💡 Recommendation")
                    st.info(result["recommendation"])

            else:
                st.error(f"Comparison failed ({resp.status_code}): {resp.text[:400]}")
        except Exception as e:
            st.error(str(e))
