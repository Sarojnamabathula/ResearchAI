#!/usr/bin/env python3
"""
ResearchAI — Application Launcher
Run the FastAPI backend or the Streamlit frontend from this entry point.

Usage:
    python run.py                  # start FastAPI backend (default)
    python run.py --frontend       # start Streamlit frontend
    python run.py --all            # start both (backend in background)
"""

from __future__ import annotations
import argparse
import subprocess
import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def start_backend(host: str = "0.0.0.0", port: int = 8000, reload: bool = False) -> None:
    cmd = [
        sys.executable, "-m", "uvicorn",
        "researchai.backend.main:app",
        "--host", host,
        "--port", str(port),
    ]
    if reload:
        cmd.append("--reload")
    print(f"[ResearchAI] Starting backend on http://{host}:{port}")
    subprocess.run(cmd, cwd=str(BASE_DIR))


def start_frontend(port: int = 8501) -> None:
    frontend_path = BASE_DIR / "frontend" / "app.py"
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(frontend_path),
        "--server.port", str(port),
        "--server.headless", "true",
    ]
    print(f"[ResearchAI] Starting frontend on http://localhost:{port}")
    subprocess.run(cmd, cwd=str(BASE_DIR))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ResearchAI Launcher")
    parser.add_argument("--frontend", action="store_true", help="Start Streamlit frontend only")
    parser.add_argument("--all", action="store_true", help="Start both backend and frontend")
    parser.add_argument("--host", default="0.0.0.0", help="Backend host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Backend port (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    if args.frontend:
        start_frontend()
    elif args.all:
        import threading
        t = threading.Thread(target=start_backend, args=(args.host, args.port, args.reload), daemon=True)
        t.start()
        start_frontend()
    else:
        start_backend(args.host, args.port, args.reload)
