# ============================================================
# Multi-Tenant Text-to-SQL Platform — Dockerfile
# Multi-stage build: builder → production
# ============================================================

# ──────────────────────────────────────────────
# Stage 1: Builder — install dependencies
# ──────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS builder

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libpq-dev \
    libssl-dev \
    libffi-dev \
    libxml2-dev \
    libxslt-dev \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# Install pip-tools for dependency management
RUN pip install --no-cache-dir --upgrade pip

WORKDIR /app

# Copy only dependency files first (layer caching)
COPY pyproject.toml ./

# Install all dependencies into /app/venv
RUN pip install --no-cache-dir --prefix=/install .


# ──────────────────────────────────────────────
# Stage 2: Production — lean final image
# ──────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS production

# Install runtime system dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libssl3 \
    libffi8 \
    libxml2 \
    libxslt1.1 \
    unixodbc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --gid 1001 appgroup \
    && useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /install /usr/local

# Copy application source code
COPY --chown=appuser:appgroup . .

# Create necessary directories
RUN mkdir -p /app/logs && chown -R appuser:appgroup /app/logs

# Switch to non-root user
USER appuser

# Expose application port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default: run the FastAPI app with Uvicorn
# Workers are determined by CPU count (2*CPUs + 1 is a common heuristic)
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--loop", "uvloop", \
     "--http", "h11", \
     "--log-config", "/dev/null", \
     "--access-log"]
