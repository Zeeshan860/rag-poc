# RAG POC Frontend

Next.js chat UI for the [RAG POC](../README.md). Upload documents, ingest URLs, view indexed sources, and ask questions with streaming answers from the FastAPI backend.

## Features

- **File upload** — PDF, DOCX, TXT, and Markdown
- **URL ingest** — Scrape and index web page content
- **Document list** — Shows ingested sources and total chunk count
- **Streaming chat** — Token-by-token responses with source citations

## Prerequisites

- Node.js 20+
- Backend running at `http://localhost:8000` (see [backend README](../backend/README.md))

## Run locally

From the `frontend` directory:

```bash
npm install
cp .env.example .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

The dev server hot-reloads when you edit files under `app/`.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Base URL of the FastAPI backend |

Copy `.env.example` to `.env.local` for local development:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

`NEXT_PUBLIC_*` variables are inlined at build time. Restart the dev server after changing them.

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server on port 3000 |
| `npm run build` | Production build |
| `npm run start` | Serve production build |
| `npm run lint` | Run ESLint |

## Project layout

```
frontend/
├── app/
│   ├── layout.tsx    # Root layout and fonts
│   └── page.tsx      # Main chat and ingest UI
├── public/           # Static assets
├── Dockerfile        # Multi-stage production image
└── .env.example      # Environment template
```

The main UI logic lives in `app/page.tsx`. It calls these backend endpoints:

- `GET /documents` — Load indexed sources on mount
- `POST /ingest/file` — Upload a file
- `POST /ingest/url` — Ingest a URL
- `POST /chat` — Stream a chat response (NDJSON)

## Run with Docker

From the repo root:

```bash
docker compose -f compose/docker-compose.yml up frontend
```

Or start the full stack:

```bash
docker compose -f compose/docker-compose.yml up
```

The compose file passes `NEXT_PUBLIC_API_URL=http://localhost:8000` as a build arg so the browser can reach the backend on the host.

## Tech stack

- [Next.js 16](https://nextjs.org/) (App Router)
- [React 19](https://react.dev/)
- [Tailwind CSS 4](https://tailwindcss.com/)
- TypeScript
