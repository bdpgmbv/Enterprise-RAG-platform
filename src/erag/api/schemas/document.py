import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentCreate(BaseModel):
    source: str = Field(max_length=64, examples=["confluence"])
    external_id: str = Field(max_length=512, examples=["98234"])
    title: str = Field(max_length=1024, examples=["Q3 Security Policy"])
    content: str

    allowed_groups: list[str] = Field(min_length=1, examples=[["engineering"]])


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: str
    external_id: str
    title: str
    content_hash: str
    created_at: datetime
    updated_at: datetime
