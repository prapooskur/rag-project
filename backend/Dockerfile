FROM python:3.12-slim-trixie
EXPOSE 7007

# various uv stuff
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_CACHE_DIR=/tmp/ragbot-cache/

# setup uv
# COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
COPY uv.lock .

# # safe to not create a venv, as we are in a container
# todo see if cache causes issues
RUN --mount=type=cache,target=/tmp/ragbot-cache/ --mount=from=ghcr.io/astral-sh/uv,source=/uv,target=/bin/uv \
  uv sync --locked

COPY . .

CMD ["/app/.venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7007"]

