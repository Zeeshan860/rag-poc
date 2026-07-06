from chromadb import Collection
from fastapi import APIRouter, Depends, File, UploadFile

from app.api.deps import get_collection, get_settings
from app.core.config import Settings
from app.schemas.ingest import IngestUrlRequest
from app.services.chunking import chunk_document
from app.services.extraction import extract_file_document, extract_url_document
from app.services.vector_store import store_chunks

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/file")
async def ingest_file(
    file: UploadFile = File(...),
    collection: Collection = Depends(get_collection),
    settings: Settings = Depends(get_settings),
):
    data = await file.read()
    document = extract_file_document(file.filename, data)
    chunks = chunk_document(document.pages, settings.chunk_size, settings.chunk_overlap)
    return store_chunks(collection, settings, file.filename, chunks)


@router.post("/url")
def ingest_url(
    body: IngestUrlRequest,
    collection: Collection = Depends(get_collection),
    settings: Settings = Depends(get_settings),
):
    document = extract_url_document(body.url)
    chunks = chunk_document(document.pages, settings.chunk_size, settings.chunk_overlap)
    return store_chunks(collection, settings, body.url, chunks)
