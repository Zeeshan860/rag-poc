# RAG POC Backend

FastAPI service that ingests documents (PDF, DOCX, TXT, MD, or URLs), stores embeddings in ChromaDB, and answers questions via Ollama.

## Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com/) running locally (or via Docker — see below)

Pull the required models:

```bash
ollama pull nomic-embed-text
ollama pull llama3.2:3b
```

## Run locally

From the `backend` directory:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # edit values as needed
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Configuration is loaded from `backend/.env` via [python-dotenv](https://github.com/theskumar/python-dotenv). Shell environment variables override `.env` values.

The API is available at [http://localhost:8000](http://localhost:8000).

Interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## Start Ollama with Docker

If you do not have Ollama installed locally, start it from the repo root:

```bash
docker compose -f compose/docker-compose.yml up ollama ollama-init
```

This starts Ollama on port `11434` and pulls the default models. Keep it running while the backend is active.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API base URL |
| `EMBED_MODEL` | `nomic-embed-text` | Model used for embeddings |
| `CHAT_MODEL` | `llama3.2:3b` | Model used for chat responses |
| `CHROMA_PATH` | `backend/data/chroma` | Directory for ChromaDB persistence |

Copy `.env.example` to `.env` and edit as needed, or set variables in your shell:

```bash
export OLLAMA_BASE_URL=http://localhost:11434
export EMBED_MODEL=nomic-embed-text
export CHAT_MODEL=llama3.2:3b
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/ingest/file` | Upload a file (PDF, DOCX, TXT, MD) |
| `POST` | `/ingest/url` | Ingest content from a URL |
| `GET` | `/documents` | List ingested sources and chunk count |
| `POST` | `/chat` | Ask a question (streaming NDJSON response) |

## Debug in VS Code / Cursor

Use the **Debug FastAPI (backend)** launch configuration in `.vscode/launch.json`. It runs uvicorn with `--reload` and the default environment variables.

## Run with Docker

From the repo root:

```bash
docker compose -f compose/docker-compose.yml up backend
```

This builds the backend image and connects it to the Ollama service defined in the same compose file.
