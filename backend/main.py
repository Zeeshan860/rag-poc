import io
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from docx import Document
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel
from pypdf import PdfReader

app = FastAPI()


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


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ingest/file")
async def ingest_file(file: UploadFile = File(...)):
    data = await file.read()
    text = extract_file_text(file.filename, data)
    chunks = chunk_text(text)
    return {
        "text_length": len(text),
        "preview": text[:300],
        "chunk_count": len(chunks),
        "chunks": chunks,
    }


@app.post("/ingest/url")
def ingest_url(body: IngestUrlRequest):
    text = extract_url_text(body.url)
    chunks = chunk_text(text)
    return {
        "text_length": len(text),
        "preview": text[:300],
        "chunk_count": len(chunks),
        "chunks": chunks,
    }
