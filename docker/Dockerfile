# Multi-stage build for production-ready AutoDevOS

# Stage 1: Python base with dependencies
FROM python:3.11-slim-bullseye as python-base
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Node.js base
FROM node:20-bullseye-slim as node-base
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Stage 3: Build stage
FROM node-base as builder
WORKDIR /app

# Copy Python dependencies from python-base
COPY --from=python-base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-base /usr/local/bin /usr/local/bin

# Copy application code
COPY package*.json ./
RUN npm ci --only=production

COPY . .

# Stage 4: Production runtime
FROM node-base as production

# Create non-root user
RUN groupadd -r autodevos && \
    useradd -r -g autodevos -u 1001 -m -s /bin/bash autodevos

WORKDIR /app

# Copy from builder
COPY --from=builder --chown=autodevos:autodevos /app /app
COPY --from=python-base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Create output directory with proper permissions
RUN mkdir -p /app/output && chown -R autodevos:autodevos /app

# Switch to non-root user
USER autodevos

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python3 -c "import sys; sys.exit(0)" || exit 1

# Entrypoint script
COPY --chown=autodevos:autodevos docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 3000 5173

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["run"]
