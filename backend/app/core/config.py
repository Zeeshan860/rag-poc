from functools import lru_cache
from pathlib import Path

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
    )

    embed_model: str = "nomic-embed-text"
    chat_model: str = "llama3.2:3b"
    ollama_base_url: str = "http://localhost:11434"
    chroma_path: str = "data/chroma"
    chunk_size: int = 900
    chunk_overlap: int = 150

    @computed_field  # type: ignore[prop-decorator]
    @property
    def resolved_chroma_path(self) -> str:
        chroma = Path(self.chroma_path)
        if not chroma.is_absolute():
            return str(BASE_DIR / self.chroma_path)
        return self.chroma_path


@lru_cache
def get_settings() -> Settings:
    return Settings()
