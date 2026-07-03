import io
import os
import re
from pathlib import Path

import chromadb
import requests
from bs4 import BeautifulSoup
from docx import Document
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel
from pypdf import PdfReader

EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
CHAT_MODEL = os.getenv("CHAT_MODEL", "llama3.2:3b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")

chroma_client = chromadb.PersistentClient(path="/data/chroma")
collection = chroma_client.get_or_create_collection("rag_docs")

app = FastAPI()


def get_embedding(text: str) -> list[float]:
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": text},
            timeout=60,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to get embedding: {exc}"
        ) from exc

    embedding = response.json().get("embedding")
    if not embedding:
        raise HTTPException(status_code=502, detail="Ollama returned no embedding")
    return embedding


def call_ollama_chat(prompt: str) -> str:
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": CHAT_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
            timeout=120,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to get chat response: {exc}"
        ) from exc

    content = response.json().get("message", {}).get("content")
    if not content:
        raise HTTPException(status_code=502, detail="Ollama returned no chat response")
    return content


def store_chunks(source: str, chunks: list[str]) -> dict:
    if not chunks:
        return {"source": source, "chunks_added": 0}

    ids, embeddings, documents, metadatas = [], [], [], []
    for i, chunk in enumerate(chunks):
        ids.append(f"{source}::{i}")
        embeddings.append(get_embedding(chunk))
        documents.append(chunk)
        metadatas.append({"source": source, "chunk_index": i})

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )
    return {"source": source, "chunks_added": len(chunks)}


def extract_pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def extract_docx(data: bytes) -> str:
    document = Document(io.BytesIO(data))
    return "\n".join(paragraph.text for paragraph in document.paragraphs)


def extract_plain_text(data: bytes) -> str:
    return data.decode("utf-8")


def extract_url_text(url: str) -> str:
    try:
        response = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "rag-poc/1.0"},
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch URL: {exc}") from exc

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup.find_all(["script", "style", "nav", "footer"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    return re.sub(r"\n{3,}", "\n\n", text)


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 150) -> list[str]:
    if not text:
        return []
    if overlap >= chunk_size:
        raise ValueError("overlap must be less than chunk_size")

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return chunks


def extract_file_text(filename: str | None, data: bytes) -> str:
    if not filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    extension = Path(filename).suffix.lower()
    if extension == ".pdf":
        return extract_pdf(data)
    if extension == ".docx":
        return extract_docx(data)
    if extension in {".txt", ".md"}:
        return extract_plain_text(data)

    raise HTTPException(status_code=400, detail="Unsupported file type")


class IngestUrlRequest(BaseModel):
    url: str


class ChatRequest(BaseModel):
    query: str
    top_k: int = 4


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ingest/file")
async def ingest_file(file: UploadFile = File(...)):
    data = await file.read()
    text = extract_file_text(file.filename, data)
    chunks = chunk_text(text)
    return store_chunks(file.filename, chunks)


@app.post("/ingest/url")
def ingest_url(body: IngestUrlRequest):
    text = extract_url_text(body.url)
    chunks = chunk_text(text)
    return store_chunks(body.url, chunks)


@app.get("/documents")
def list_documents():
    count = collection.count()
    if count == 0:
        return {"sources": [], "total_chunks": 0}

    result = collection.get(include=["metadatas"])
    sources = sorted({m["source"] for m in result["metadatas"]})
    return {"sources": sources, "total_chunks": count}


@app.post("/chat")
def chat(body: ChatRequest):
    if collection.count() == 0:
        raise HTTPException(
            status_code=400,
            detail="No documents ingested. Upload a file or URL first.",
        )

    query_embedding = get_embedding(body.query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=body.top_k,
        include=["documents", "metadatas"],
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    context = "\n\n".join(documents)

    prompt = (
        "You are a helpful assistant. Answer the question using ONLY the context below.\n"
        "If the answer is not in the context, respond with exactly: I don't know\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {body.query}"
    )

    answer = call_ollama_chat(prompt)
    sources = sorted({m["source"] for m in metadatas})
    return {"answer": answer, "sources": sources}
