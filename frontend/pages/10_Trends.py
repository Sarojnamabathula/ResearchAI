"""
ResearchAI — Page 10: Trend Analysis
Publication trends, keyword clouds, top authors, venues, and growth.
"""

import streamlit as st
import requests
import os
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="Trends — ResearchAI", page_icon="📈", layout="wide")

API_BASE = os.getenv("RESEARCHAI_API_URL", "http://localhost:8000")

st.title("📈 Trend Analysis")
st.caption("Explore publication trends, popular keywords, and emerging research topics.")

# ── Load Papers ───────────────────────────────────────────────────────────────
try:
    r = requests.get(f"{API_BASE}/api/papers", params={"limit": 200}, timeout=10)
    papers = r.json() if r.status_code == 200 else []
except Exception:
    papers = []

paper_map = {p["id"]: f"{p.get('title','')[:70]} ({p.get('year','?')})" for p in papers}

if not papers:
    st.info("No papers indexed yet. Search and process papers first.")
    st.stop()

# ── Form ──────────────────────────────────────────────────────────────────────
topic = st.text_input("Research Topic (for AI trend analysis)", placeholder="e.g. Deep Learning")
use_all = st.checkbox("Analyse all indexed papers", value=True)
if not use_all:
    selected_ids = st.multiselect(
        "Select papers",
        options=list(paper_map.keys()),
        format_func=lambda pid: paper_map.get(pid, pid),
    )
else:
    selected_ids = []

if st.button("📈 Analyse Trends", use_container_width=True, type="primary"):
    if not topic:
        st.warning("Please enter a topic.")
        st.stop()
    with st.spinner("Analysing trends…"):
        try:
            resp = requests.post(
                f"{API_BASE}/api/trends/analyze",
                json={"topic": topic, "paper_ids": selected_ids, "use_all_papers": use_all},
                timeout=180,
            )
            if resp.status_code == 200:
                result = resp.json()

                # ── Summary Metrics ───────────────────────────────────────
                m1, m2, m3 = st.columns(3)
                m1.metric("Papers Analysed", len(papers))
                m2.metric("Growth Rate", f"{result.get('growth_rate', 0):.1%}")
                m3.metric("Emerging Topics", len(result.get("emerging_topics", [])))

                st.markdown("---")

                # ── Publication Trends Chart ──────────────────────────────
                pub_trends = result.get("publication_trends", [])
                if pub_trends:
                    st.subheader("Publications per Year")
                    for td in pub_trends:
                        if td.get("years") and td.get("values"):
                            df_trend = pd.DataFrame(
                                {"Year": td["years"], "Papers": td["values"]}
                            )
                            fig = px.bar(
                                df_trend,
                                x="Year",
                                y="Papers",
                                title=td.get("label", ""),
                                color_discrete_sequence=["#3b82d4"],
                            )
                            st.plotly_chart(fig, use_container_width=True)

                col1, col2 = st.columns(2)

                # ── Top Keywords ──────────────────────────────────────────
                with col1:
                    kw = result.get("top_keywords", [])
                    if kw:
                        st.subheader("Top Keywords")
                        df_kw = pd.DataFrame(kw).rename(
                            columns={"keyword": "Keyword", "count": "Count"}
                        )
                        if not df_kw.empty:
                            fig_kw = px.bar(
                                df_kw.head(15),
                                x="Count",
                                y="Keyword",
                                orientation="h",
                                color_discrete_sequence=["#7c5cd8"],
                            )
                            fig_kw.update_layout(yaxis=dict(autorange="reversed"))
                            st.plotly_chart(fig_kw, use_container_width=True)

                # ── Most Active Authors ───────────────────────────────────
                with col2:
                    authors = result.get("most_active_authors", [])
                    if authors:
                        st.subheader("Most Active Authors")
                        df_auth = pd.DataFrame(authors).rename(
                            columns={"author": "Author", "count": "Papers"}
                        )
                        st.dataframe(df_auth.head(10), use_container_width=True)

                # ── Venues ────────────────────────────────────────────────
                venues = result.get("most_active_venues", [])
                if venues:
                    st.subheader("Most Active Venues")
                    df_v = pd.DataFrame(venues).rename(
                        columns={"venue": "Venue", "count": "Papers"}
                    )
                    fig_v = px.pie(
                        df_v.head(10),
                        names="Venue",
                        values="Papers",
                        title="Publication Venues",
                    )
                    st.plotly_chart(fig_v, use_container_width=True)

                # ── Emerging Topics ───────────────────────────────────────
                emerging = result.get("emerging_topics", [])
                if emerging:
                    st.subheader("🚀 Emerging Topics")
                    for t in emerging:
                        st.markdown(f"- {t}")

            else:
                st.error(f"Failed ({resp.status_code}): {resp.text[:400]}")
        except Exception as e:
            st.error(str(e))
