import json

import requests
from fastapi import HTTPException

from app.core.config import Settings


def get_embedding(text: str, settings: Settings) -> list[float]:
    try:
        response = requests.post(
            f"{settings.ollama_base_url}/api/embeddings",
            json={"model": settings.embed_model, "prompt": text},
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


def stream_ollama_chat(prompt: str, sources: list[str], settings: Settings):
    try:
        response = requests.post(
            f"{settings.ollama_base_url}/api/chat",
            json={
                "model": settings.chat_model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": True,
            },
            stream=True,
            timeout=120,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to get chat response: {exc}"
        ) from exc

    for line in response.iter_lines():
        if not line:
            continue
        chunk = json.loads(line)
        token = chunk.get("message", {}).get("content", "")
        if token:
            yield json.dumps({"token": token}) + "\n"
        if chunk.get("done"):
            break

    yield json.dumps({"done": True, "sources": sources}) + "\n"
