FROM python:3.12-slim-trixie
EXPOSE 7007

# various uv stuff
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_CACHE_DIR=/root/.cache/uv

# setup uv
# COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
COPY uv.lock .

# # safe to not create a venv, as we are in a container
# todo see if cache causes issues
RUN --mount=type=cache,target=/root/.cache/uv --mount=from=ghcr.io/astral-sh/uv,source=/uv,target=/bin/uv \
  uv sync --locked --no-dev

COPY . .

# Pre-download HuggingFace models during build with cache mount
# This prevents downloading models on every container start
RUN --mount=type=cache,target=/root/.cache/huggingface \
  /app/.venv/bin/python -c "\
from llama_index.embeddings.huggingface import HuggingFaceEmbedding; \
from llama_index.core.postprocessor import SentenceTransformerRerank; \
print('Downloading embedding model...'); \
embed = HuggingFaceEmbedding(model_name='Qwen/Qwen3-Embedding-0.6B'); \
print('Downloading reranker model...'); \
rerank = SentenceTransformerRerank(model='BAAI/bge-reranker-v2-m3', top_n=5); \
print('Models downloaded successfully')"

CMD ["/app/.venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7007"]

