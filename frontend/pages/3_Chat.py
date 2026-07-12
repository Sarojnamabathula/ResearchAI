"""
ResearchAI — Page 3: Research Chat (RAG)
Conversational Q&A grounded in your indexed research papers.
"""

import streamlit as st
import requests
import os

st.set_page_config(page_title="Chat — ResearchAI", page_icon="💬", layout="wide")

API_BASE = os.getenv("RESEARCHAI_API_URL", "http://localhost:8000")

st.title("💬 Research Chat")
st.caption("Ask questions over your indexed papers. All answers are grounded in real research.")

# ── Session State ─────────────────────────────────────────────────────────────
if "chat_session_id" not in st.session_state:
    st.session_state.chat_session_id = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ── Sidebar: Paper Selection & Session Control ────────────────────────────────
with st.sidebar:
    st.subheader("Chat Settings")

    try:
        r = requests.get(f"{API_BASE}/api/papers", params={"limit": 100}, timeout=5)
        papers = r.json() if r.status_code == 200 else []
    except Exception:
        papers = []

    paper_map = {p["id"]: f"{p.get('title','')[:60]} ({p.get('year','?')})" for p in papers}
    selected_paper_ids = st.multiselect(
        "Scope to papers (optional)",
        options=list(paper_map.keys()),
        format_func=lambda pid: paper_map.get(pid, pid),
        help="Leave empty to search across all indexed papers.",
    )

    if st.button("🆕 New Session"):
        with st.spinner("Creating session…"):
            try:
                resp = requests.post(
                    f"{API_BASE}/api/chat/session",
                    json={"paper_ids": selected_paper_ids},
                    timeout=10,
                )
                if resp.status_code == 200:
                    d = resp.json()
                    st.session_state.chat_session_id = d.get("session_id")
                    st.session_state.chat_history = []
                    st.success(f"Session: `{st.session_state.chat_session_id[:8]}…`")
                else:
                    st.error("Failed to create session")
            except Exception as e:
                st.error(str(e))

    if st.session_state.chat_session_id:
        st.info(f"Session: `{st.session_state.chat_session_id[:8]}…`")

# ── Start session automatically if none exists ────────────────────────────────
if not st.session_state.chat_session_id:
    try:
        resp = requests.post(
            f"{API_BASE}/api/chat/session",
            json={"paper_ids": []},
            timeout=10,
        )
        if resp.status_code == 200:
            st.session_state.chat_session_id = resp.json().get("session_id")
    except Exception:
        pass

# ── Chat Display ──────────────────────────────────────────────────────────────
chat_container = st.container()
with chat_container:
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg.get("sources"):
                with st.expander("📚 Sources", expanded=False):
                    for src in msg["sources"]:
                        st.caption(f"• {src}")
            if msg.get("confidence") is not None and msg["role"] == "assistant":
                st.caption(f"Confidence: {msg['confidence']:.0%}  |  {msg.get('reasoning', '')}")

# ── Chat Input ────────────────────────────────────────────────────────────────
user_input = st.chat_input("Ask a research question…")

if user_input:
    if not st.session_state.chat_session_id:
        st.error("No active chat session. Click 'New Session' in the sidebar.")
    else:
        # Display user message immediately
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)

        # Send to API
        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                try:
                    resp = requests.post(
                        f"{API_BASE}/api/chat/message",
                        json={
                            "session_id": st.session_state.chat_session_id,
                            "message": user_input,
                            "paper_ids": selected_paper_ids,
                        },
                        timeout=120,
                    )
                    if resp.status_code == 200:
                        d = resp.json()
                        answer = d.get("answer", "No answer returned.")
                        sources = d.get("sources_used", [])
                        confidence = d.get("confidence", 0.0)
                        reasoning = d.get("reasoning", "")

                        st.write(answer)
                        if sources:
                            with st.expander("📚 Sources", expanded=False):
                                for s in sources:
                                    st.caption(f"• {s}")
                        st.caption(f"Confidence: {confidence:.0%}  |  {reasoning}")

                        # Append to history
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": answer,
                            "sources": sources,
                            "confidence": confidence,
                            "reasoning": reasoning,
                        })
                    else:
                        err = f"API error ({resp.status_code}): {resp.text[:300]}"
                        st.error(err)
                        st.session_state.chat_history.append({
                            "role": "assistant", "content": err,
                        })
                except requests.exceptions.ConnectionError:
                    st.error("Backend offline. Start with: `python run.py`")
                except Exception as e:
                    st.error(str(e))

# ── Example Questions ─────────────────────────────────────────────────────────
with st.expander("💡 Example Questions"):
    examples = [
        "Summarize the main contribution of the first paper.",
        "What methodology does this paper use?",
        "List the limitations mentioned across the papers.",
        "What datasets were used in these studies?",
        "Compare the results reported in the papers.",
        "What future work do the authors suggest?",
        "Explain the key algorithm in beginner-friendly terms.",
    ]
    for ex in examples:
        st.markdown(f"- *{ex}*")
