"""What the API accepts and returns for documents."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentCreate(BaseModel):
    """Body of a create request."""

    source: str = Field(max_length=64, examples=["confluence"])
    external_id: str = Field(max_length=512, examples=["98234"])
    title: str = Field(max_length=1024, examples=["Q3 Security Policy"])
    # The full text. We hash it to detect changes.
    content: str


class DocumentRead(BaseModel):
    """What we return to the caller."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: str
    external_id: str
    title: str
    content_hash: str
    created_at: datetime
    updated_at: datetime
