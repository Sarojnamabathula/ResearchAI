"""
ResearchAI — Page 11: Settings
Configure API endpoint, view system info, manage data.
"""

import streamlit as st
import requests
import os

st.set_page_config(page_title="Settings — ResearchAI", page_icon="⚙️", layout="wide")

API_BASE_DEFAULT = os.getenv("RESEARCHAI_API_URL", "http://localhost:8000")

st.title("⚙️ Settings")
st.caption("Configure the ResearchAI application.")

# ── API Connection ────────────────────────────────────────────────────────────
st.subheader("API Connection")
api_url = st.text_input("Backend API URL", value=API_BASE_DEFAULT)

col1, col2 = st.columns(2)
with col1:
    if st.button("🔍 Test Connection"):
        try:
            r = requests.get(f"{api_url}/api/health", timeout=5)
            if r.status_code == 200:
                d = r.json()
                st.success(f"✅ Connected — Version: {d.get('version','?')}")
                if d.get("watsonx_configured"):
                    st.success("✅ IBM watsonx credentials configured")
                else:
                    st.warning(
                        "⚠️ IBM watsonx not configured. "
                        "Set WATSONX_API_KEY and WATSONX_PROJECT_ID in your .env file."
                    )
            else:
                st.error(f"❌ HTTP {r.status_code}")
        except Exception as e:
            st.error(f"❌ Connection failed: {e}")

# ── System Info ───────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("System Information")
try:
    r = requests.get(f"{api_url}/api/info", timeout=5)
    if r.status_code == 200:
        info = r.json()
        col1, col2 = st.columns(2)
        col1.markdown(f"**App Name:** {info.get('name','?')}")
        col1.markdown(f"**Version:** {info.get('version','?')}")
        col1.markdown(f"**AI Model:** {info.get('model','?')}")
        col2.markdown(f"**Vector Store:** {info.get('vector_store','?')}")

        if info.get("modules"):
            st.markdown("**Active Modules:**")
            cols = st.columns(3)
            for i, mod in enumerate(info["modules"]):
                cols[i % 3].markdown(f"- {mod.replace('_',' ').title()}")
except Exception:
    st.warning("System info unavailable — is the backend running?")

# ── Database Stats ────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Database Statistics")
try:
    rp = requests.get(f"{api_url}/api/papers", params={"limit": 1000}, timeout=10)
    rr = requests.get(f"{api_url}/api/reports", timeout=10)
    paper_count = len(rp.json()) if rp.status_code == 200 else "?"
    report_count = len(rr.json()) if rr.status_code == 200 else "?"

    col1, col2 = st.columns(2)
    col1.metric("Papers Indexed", paper_count)
    col2.metric("Reports Generated", report_count)
except Exception:
    st.warning("Could not fetch database statistics.")

# ── Quick Setup Guide ─────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Quick Setup Guide")
with st.expander("How to configure IBM watsonx credentials"):
    st.markdown(
        """
1. Create an [IBM Cloud account](https://cloud.ibm.com/registration)
2. Provision a **watsonx.ai** service instance
3. Create an [API key](https://cloud.ibm.com/iam/apikeys)
4. Create a **watsonx.ai project** and copy the Project ID
5. Copy `.env.example` to `.env` in the project root
6. Set `WATSONX_API_KEY` and `WATSONX_PROJECT_ID`
7. Restart the backend: `python run.py`
        """
    )

with st.expander("Installation & Running"):
    st.code(
        """# 1. Clone and install
git clone <repo>
cd researchai
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env with your credentials

# 3. Run backend
python run.py

# 4. Run frontend (in another terminal)
python run.py --frontend

# 5. Or run both together
python run.py --all
""",
        language="bash",
    )

with st.expander("Docker Deployment"):
    st.code(
        """# Build and start
docker compose up --build

# Stop
docker compose down
""",
        language="bash",
    )
