"""
ResearchAI — Page 9: Research Timeline
Chronological evolution of a research field.
"""

import streamlit as st
import requests
import os
import plotly.graph_objects as go

st.set_page_config(page_title="Timeline — ResearchAI", page_icon="📅", layout="wide")

API_BASE = os.getenv("RESEARCHAI_API_URL", "http://localhost:8000")

st.title("📅 Research Timeline")
st.caption("Visualize the chronological evolution of a research field.")

# ── Load Papers ───────────────────────────────────────────────────────────────
try:
    r = requests.get(f"{API_BASE}/api/papers", params={"limit": 100}, timeout=10)
    papers = r.json() if r.status_code == 200 else []
except Exception:
    papers = []

paper_map = {p["id"]: f"{p.get('title','')[:70]} ({p.get('year','?')})" for p in papers}

# ── Form ──────────────────────────────────────────────────────────────────────
topic = st.text_input("Research Topic", placeholder="e.g. Transformer architecture evolution")
use_all = st.checkbox("Use all indexed papers", value=True)
if not use_all:
    selected_ids = st.multiselect(
        "Select papers",
        options=list(paper_map.keys()),
        format_func=lambda pid: paper_map.get(pid, pid),
    )
else:
    selected_ids = []

gen_btn = st.button("📅 Generate Timeline", use_container_width=True, type="primary")

if gen_btn:
    if not topic:
        st.warning("Please enter a research topic.")
        st.stop()
    with st.spinner("Building research timeline…"):
        try:
            resp = requests.post(
                f"{API_BASE}/api/timeline/generate",
                json={"topic": topic, "paper_ids": selected_ids, "use_all_papers": use_all},
                timeout=300,
            )
            if resp.status_code == 200:
                timeline = resp.json()
                events = sorted(timeline.get("events", []), key=lambda e: e.get("year", 0))

                if events:
                    # ── Plotly timeline chart ─────────────────────────────
                    fig = go.Figure()
                    years = [e["year"] for e in events]
                    titles = [e.get("title", "")[:40] for e in events]
                    descs = [e.get("description", "")[:100] for e in events]

                    fig.add_trace(
                        go.Scatter(
                            x=years,
                            y=[1] * len(events),
                            mode="markers+text",
                            text=titles,
                            textposition="top center",
                            marker=dict(size=14, color="#3b82d4"),
                            hovertemplate=(
                                "<b>%{x}</b><br>%{text}<br>"
                                + "<br>".join(f"{d}" for d in descs)
                                + "<extra></extra>"
                            ),
                            customdata=descs,
                        )
                    )
                    fig.update_layout(
                        title=f"Research Timeline: {topic}",
                        xaxis_title="Year",
                        yaxis=dict(visible=False),
                        height=300,
                        showlegend=False,
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # ── Event list ────────────────────────────────────────
                    st.subheader("Events")
                    for e in events:
                        with st.container(border=True):
                            e_col1, e_col2 = st.columns([1, 5])
                            e_col1.metric("Year", e.get("year", "?"))
                            e_col2.markdown(f"**{e.get('title', '')}**")
                            e_col2.write(e.get("description", ""))
                            if e.get("significance"):
                                e_col2.caption(f"Significance: {e['significance']}")

                else:
                    st.info("No timeline events generated. Try adding more papers.")

                if timeline.get("narrative"):
                    st.subheader("Field Evolution Narrative")
                    st.write(timeline["narrative"])

            else:
                st.error(f"Failed ({resp.status_code}): {resp.text[:400]}")
        except Exception as e:
            st.error(str(e))
