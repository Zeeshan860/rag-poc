# RAG POC

A proof-of-concept retrieval-augmented generation (RAG) application. Upload documents or ingest web pages, then ask questions grounded in that content. The stack is fully local: embeddings and chat run through [Ollama](https://ollama.com/), vectors are stored in [ChromaDB](https://www.trychroma.com/), and the UI is a [Next.js](https://nextjs.org/) frontend talking to a [FastAPI](https://fastapi.tiangolo.com/) backend.

## Architecture

```
┌─────────────┐     HTTP      ┌─────────────┐     HTTP      ┌─────────────┐
│   Next.js   │ ────────────► │   FastAPI   │ ────────────► │   Ollama    │
│  frontend   │  :3000        │   backend   │  :11434       │  (models)   │
│             │               │             │               │             │
└─────────────┘               │      │      │               └─────────────┘
                              │      ▼      │
                              │  ChromaDB   │
                              │  (vectors)  │
                              └─────────────┘
```

| Component | Role |
|-----------|------|
| **Frontend** (`frontend/`) | Chat UI, file upload, URL ingest, document list |
| **Backend** (`backend/`) | Text extraction, chunking, embedding, vector search, streaming chat |
| **Ollama** | `nomic-embed-text` for embeddings, `llama3.2:3b` for answers |
| **ChromaDB** | Persistent vector store for document chunks |

## Quick start (Docker)

The fastest way to run everything:

```bash
docker compose -f compose/docker-compose.yml up
```

This starts Ollama (and pulls models), the backend on port `8000`, and the frontend on port `3000`. Open [http://localhost:3000](http://localhost:3000).

To run only Ollama (for local development of backend/frontend):

```bash
docker compose -f compose/docker-compose.yml up ollama ollama-init
```

## Quick start (local development)

### 1. Start Ollama

Install [Ollama](https://ollama.com/) locally, or use Docker as above. Pull the required models:

```bash
ollama pull nomic-embed-text
ollama pull llama3.2:3b
```

### 2. Start the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 3. Start the frontend

In a second terminal:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Usage

1. **Ingest** — Upload a PDF, DOCX, TXT, or Markdown file, or paste a URL to scrape page content.
2. **Ask** — Type a question in the chat. The backend retrieves relevant chunks and streams an answer from Ollama.
3. **Sources** — Each answer lists which ingested documents were used.

Supported ingest formats: `.pdf`, `.docx`, `.txt`, `.md`, and HTTP/HTTPS URLs.

## Project structure

```
rag-poc/
├── backend/          # FastAPI service (ingest, search, chat)
├── frontend/         # Next.js chat UI
├── compose/          # Docker Compose stack
└── .vscode/          # VS Code / Cursor debug configs
```

## Documentation

- [Backend README](backend/README.md) — API endpoints, environment variables, Docker
- [Frontend README](frontend/README.md) — UI setup, configuration, development

## Requirements

- **Docker path:** Docker and Docker Compose
- **Local path:** Python 3.11+, Node.js 20+, Ollama

## License

Proof of concept — use and adapt as needed.
