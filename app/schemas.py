from typing import Optional
from pydantic import BaseModel


class Item(BaseModel):
    title: str
    summary: str
    source: Optional[str] = None
    published_at: Optional[str] = None
    url: Optional[str] = None