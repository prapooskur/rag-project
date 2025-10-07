Frontend: Discord.js bot

Backend: LlamaIndex+FastAPI server


## Setup
- Create `.env` files in both `bot` and `backend` based on `.env.example`s
- If using OpenAI backend, make sure to set OpenAI key
- If using Ollama backend, ensure Ollama is installed and up to date

## Run in Production:
- Run `docker compose up -d`

## Develop locally with Docker:
- From main directory, run `docker compose build`
- Run `docker compose up -d`

## Develop locally with bare-metal
### Prerequisites:
- PostgreSQL with pgvector extension installed
- Node.js and pnpm (for bot)
- Python 3.12+ and uv (for backend)
- Ollama (if using local LLM) or OpenAI API key

### Database Setup:
1. Start PostgreSQL server: `docker compose up -d rag-database`
- Uncomment `ports:` section in `docker-compose.yml` first.

### Backend:
1. Navigate to `backend/` directory: `cd backend/`
2. Install dependencies: `uv sync`
3. Create `.env` file based on `.env.example`
4. Configure your LLM provider (OpenAI or Ollama) and model in `.env`
5. Run the backend server: `uv run fastapi dev main.py`

### Bot:
1. Navigate to `bot/` directory: `cd bot/`
2. Install dependencies: `pnpm install`
3. Create `.env` file based on `.env.example`
4. Deploy slash commands: `pnpm run deploy`
5. Run the bot in development mode: `pnpm run dev`
