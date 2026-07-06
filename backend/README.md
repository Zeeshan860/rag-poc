# RAG POC Backend

FastAPI service that ingests documents (PDF, DOCX, TXT, MD, or URLs), chunks and embeds them with Ollama, stores vectors in ChromaDB, and answers questions via streaming chat.

Part of the [RAG POC](../README.md) monorepo. The frontend lives in `frontend/`.

## How it works

1. **Ingest** — Files and URLs are parsed to plain text, split into overlapping chunks (~900 chars, 150 overlap), and embedded via Ollama (`nomic-embed-text`).
2. **Store** — Chunks and embeddings are persisted in a local ChromaDB collection (`rag_docs`).
3. **Chat** — A user query is embedded, the top-k similar chunks are retrieved, and Ollama (`llama3.2:3b`) streams an answer constrained to that context.

## Project structure

```text
backend/
├── main.py              # entrypoint shim (uvicorn main:app)
└── app/
    ├── main.py          # FastAPI app factory + CORS + routers
    ├── core/config.py   # Settings (pydantic-settings, loads .env)
    ├── db/chroma.py     # ChromaDB client and collection
    ├── schemas/         # Pydantic request models
    ├── services/        # business logic (Ollama, extraction, chunking, vector store)
    └── api/
        ├── deps.py      # FastAPI dependency injection helpers
        └── routes/      # API route handlers
```

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

Configuration is loaded from `backend/.env` and environment variables via [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) in `app/core/config.py`. Shell environment variables override `.env` values.

- API: [http://localhost:8000](http://localhost:8000)
- Interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs)

CORS is enabled for `http://localhost:3000` (the frontend dev server).

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
| `CHROMA_PATH` | `./data/chroma` | Directory for ChromaDB persistence (relative to `backend/`) |

Copy `.env.example` to `.env` and edit as needed:

```bash
OLLAMA_BASE_URL=http://localhost:11434
EMBED_MODEL=nomic-embed-text
CHAT_MODEL=llama3.2:3b
CHROMA_PATH=./data/chroma
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/ingest/file` | Upload a file (PDF, DOCX, TXT, MD) — multipart form field `file` |
| `POST` | `/ingest/url` | Ingest content from a URL — JSON body `{ "url": "..." }` |
| `GET` | `/documents` | List ingested sources and total chunk count |
| `POST` | `/chat` | Ask a question — JSON body `{ "query": "...", "top_k": 4 }`, returns streaming NDJSON |

### Chat response format

The `/chat` endpoint streams newline-delimited JSON:

```json
{"token": "Hello"}
{"token": " world"}
{"done": true, "sources": ["doc.pdf", "https://example.com"]}
```

## Debug in VS Code / Cursor

Use the **Debug FastAPI (backend)** launch configuration in `.vscode/launch.json`. It runs uvicorn with `--reload` and the default environment variables.

## Run with Docker

From the repo root:

```bash
docker compose -f compose/docker-compose.yml up backend
```

This builds the backend image and connects it to the Ollama service defined in the same compose file. ChromaDB data is stored in a Docker volume (`chroma_data`).

To run the full stack (Ollama + backend + frontend):

```bash
docker compose -f compose/docker-compose.yml up
```

## Dependencies

See `requirements.txt`. Key libraries: FastAPI, pydantic-settings, ChromaDB, pypdf, python-docx, BeautifulSoup4, requests.
