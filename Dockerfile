# Accounting MCP — deterministic nhật ký chung → T-account export
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements_mcp.txt .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements_mcp.txt

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r appuser -g 1000 && \
    useradd -r -u 1000 -g appuser -s /sbin/nologin -c "Application user" appuser

COPY --from=builder /opt/venv /opt/venv
COPY . .
RUN mkdir -p /tmp/accounting-artifacts && chown -R appuser:appuser /app /opt/venv /tmp/accounting-artifacts

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ACCOUNTING_ARTIFACT_DIR=/tmp/accounting-artifacts

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000
USER appuser
CMD ["uvicorn", "app.mcp_server:http_app", "--host", "0.0.0.0", "--port", "8000"]
