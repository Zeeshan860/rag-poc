from chromadb import Collection
from fastapi import APIRouter, Depends

from app.api.deps import get_collection
from app.services.vector_store import list_documents

router = APIRouter(tags=["documents"])


@router.get("/documents")
def get_documents(collection: Collection = Depends(get_collection)):
    return list_documents(collection)
