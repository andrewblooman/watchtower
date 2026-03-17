#  Stage 1: Build Next.js static UI ─
FROM node:20-alpine AS ui-builder

WORKDIR /ui
COPY ui/package*.json ./
RUN npm ci

COPY ui/ ./

# Empty string = same-origin API calls (served by FastAPI on the same port).
# Override NEXT_PUBLIC_API_BASE at build time if needed.
ARG NEXT_PUBLIC_API_BASE=""
ENV NEXT_PUBLIC_API_BASE=$NEXT_PUBLIC_API_BASE

RUN npm run build
# Output is in /ui/out/


#  Stage 2: Python runtime (API + agent) 
FROM python:3.12-slim

LABEL org.opencontainers.image.title="SRE Agent" \
      org.opencontainers.image.description="Ephemeral ECS debugging agent with Bedrock reasoning" \
      org.opencontainers.image.source="https://github.com/your-org/sre-agent"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app/    /app/app/
COPY agent/  /app/agent/
COPY entrypoint.sh /app/entrypoint.sh
# Strip Windows CRLF line endings so the script runs correctly on Linux
RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Copy the built Next.js static files into the image
COPY --from=ui-builder /ui/out /app/ui_static

# Create a non-root user and hand over ownership of app files + cache dir
RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup appuser \
    && mkdir -p /data/cache \
    && chown -R appuser:appgroup /app /data/cache

VOLUME ["/data/cache"]

USER appuser

EXPOSE 8000

# Health check uses Python stdlib so no extra tools are required in the slim image
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')" 2>/dev/null || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
