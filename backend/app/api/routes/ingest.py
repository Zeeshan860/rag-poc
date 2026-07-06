from chromadb import Collection
from fastapi import APIRouter, Depends, File, UploadFile

from app.api.deps import get_collection, get_settings
from app.core.config import Settings
from app.schemas.ingest import IngestUrlRequest
from app.services.chunking import chunk_text
from app.services.extraction import extract_file_text, extract_url_text
from app.services.vector_store import store_chunks

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/file")
async def ingest_file(
    file: UploadFile = File(...),
    collection: Collection = Depends(get_collection),
    settings: Settings = Depends(get_settings),
):
    data = await file.read()
    text = extract_file_text(file.filename, data)
    chunks = chunk_text(text)
    return store_chunks(collection, settings, file.filename, chunks)


@router.post("/url")
def ingest_url(
    body: IngestUrlRequest,
    collection: Collection = Depends(get_collection),
    settings: Settings = Depends(get_settings),
):
    text = extract_url_text(body.url)
    chunks = chunk_text(text)
    return store_chunks(collection, settings, body.url, chunks)
