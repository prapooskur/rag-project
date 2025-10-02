FROM python:3.12-slim-trixie

# setup uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY . /app
WORKDIR /app

# safe to not create a venv, as we are in a container
RUN uv pip install --system -r ./pyproject.toml

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

