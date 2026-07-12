# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy source code
COPY . .

# Create required data directories
RUN mkdir -p data/papers data/embeddings/chroma data/reports data/logs

# Expose ports
EXPOSE 8000
EXPOSE 8501

# Default: start the FastAPI backend
CMD ["python", "-m", "uvicorn", "researchai.backend.main:app", \
     "--host", "0.0.0.0", "--port", "8000"]
