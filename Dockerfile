# Production Dockerfile for hosting platforms (Render, Railway, Fly.io)
FROM python:3.12-slim

# Faster image, more secure
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install deps first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY app/ app/
COPY templates/ templates/
COPY static/ static/
COPY prompts/ prompts/

# Non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Render/Railway/Fly all pass PORT as env var
ENV PORT=8000
EXPOSE 8000

# Use shell form so $PORT gets expanded at runtime
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
