FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /uvx /usr/local/bin/
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev
COPY app ./app
COPY public ./public
COPY alembic ./alembic
COPY alembic.ini ./
RUN useradd --uid 10001 --create-home api
USER api
EXPOSE 3000
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 3000"]
