from chromadb import Collection
from fastapi import HTTPException

from app.core.config import Settings
from app.services.chunking import TextChunk
from app.services.ollama import get_embedding


def store_chunks(
    collection: Collection,
    settings: Settings,
    source: str,
    chunks: list[TextChunk],
) -> dict:
    if not chunks:
        return {"source": source, "chunks_added": 0}

    ids, embeddings, documents, metadatas = [], [], [], []
    for chunk in chunks:
        ids.append(f"{source}::{chunk.chunk_index}")
        embeddings.append(get_embedding(chunk.text, settings))
        documents.append(chunk.text)
        metadata: dict = {"source": source, "chunk_index": chunk.chunk_index}
        if chunk.page_number is not None:
            metadata["page_number"] = chunk.page_number
        metadatas.append(metadata)

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )
    return {"source": source, "chunks_added": len(chunks)}


def list_documents(collection: Collection) -> dict:
    count = collection.count()
    if count == 0:
        return {"sources": [], "total_chunks": 0}

    result = collection.get(include=["metadatas"])
    sources = sorted({m["source"] for m in result["metadatas"]})
    return {"sources": sources, "total_chunks": count}


def retrieve_context(
    collection: Collection,
    settings: Settings,
    query: str,
    top_k: int,
) -> tuple[str, list[str]]:
    if collection.count() == 0:
        raise HTTPException(
            status_code=400,
            detail="No documents ingested. Upload a file or URL first.",
        )

    query_embedding = get_embedding(query, settings)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas"],
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    context = "\n\n".join(documents)
    sources = sorted({m["source"] for m in metadatas})
    return context, sources
