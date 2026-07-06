from pydantic import BaseModel


class IngestUrlRequest(BaseModel):
    url: str
