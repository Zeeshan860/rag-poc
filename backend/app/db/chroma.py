import chromadb
from chromadb import Collection

from app.core.config import Settings, get_settings

_client = None
_collection = None


def get_chroma_client(settings: Settings | None = None) -> chromadb.PersistentClient:
    global _client
    if _client is None:
        settings = settings or get_settings()
        _client = chromadb.PersistentClient(path=settings.resolved_chroma_path)
    return _client


def get_collection(settings: Settings | None = None) -> Collection:
    global _collection
    if _collection is None:
        client = get_chroma_client(settings)
        _collection = client.get_or_create_collection("rag_docs")
    return _collection
