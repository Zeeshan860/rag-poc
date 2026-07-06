from chromadb import Collection
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import get_collection, get_settings
from app.core.config import Settings
from app.schemas.chat import ChatRequest
from app.services.ollama import stream_ollama_chat
from app.services.vector_store import retrieve_context

router = APIRouter(tags=["chat"])


@router.post("/chat")
def chat(
    body: ChatRequest,
    collection: Collection = Depends(get_collection),
    settings: Settings = Depends(get_settings),
):
    context, sources = retrieve_context(
        collection, settings, body.query, body.top_k
    )

    prompt = (
        "You are a helpful assistant. Answer the question using ONLY the context below.\n"
        "If the answer is not in the context, respond with exactly: I don't know\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {body.query}"
    )

    return StreamingResponse(
        stream_ollama_chat(prompt, sources, settings),
        media_type="application/x-ndjson",
    )
