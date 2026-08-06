# syntax=docker/dockerfile:1

# --- Builder: install Python dependencies into a venv ---
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# --- Runtime: slim image with only what's needed to run ---
FROM python:3.11-slim AS runtime

WORKDIR /app

# git is required at runtime, not just build time: GitPython (app/repository_processor/
# github_cloner.py) shells out to the real `git` binary to clone repositories.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash nexus

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY . .

RUN mkdir -p storage/uploads storage/repos \
    && chmod +x docker-entrypoint.sh \
    && chown -R nexus:nexus /app

USER nexus

EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
