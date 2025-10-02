FROM python:3.12-slim-trixie

# setup uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies
COPY pyproject.toml .

# safe to not create a venv, as we are in a container
RUN uv venv
RUN uv pip install -r ./pyproject.toml

COPY . .

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

