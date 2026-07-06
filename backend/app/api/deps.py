from chromadb import Collection
from fastapi import Depends

from app.core.config import Settings, get_settings as _get_settings
from app.db.chroma import get_collection as _get_collection


def get_settings() -> Settings:
    return _get_settings()


def get_collection(settings: Settings = Depends(get_settings)) -> Collection:
    return _get_collection(settings)
