FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY gateway/ ./gateway/
COPY layers/ ./layers/
COPY pipelines/ ./pipelines/
COPY orchestrator/ ./orchestrator/
COPY mcp/ ./mcp/
COPY studio/ ./studio/

# Create runtime directories
RUN mkdir -p /app/facts /app/vector_db /app/logs /app/blueprints /app/seed

# Copy seed data
COPY seed/ ./seed/

EXPOSE 8000 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
