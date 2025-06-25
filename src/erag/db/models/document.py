"""A document we have ingested."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from erag.db.base import Base


class Document(Base):
    """One source document, before it is split into chunks."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Where it came from: confluence, jira, slack, filesystem.
    source: Mapped[str] = mapped_column(String(64), index=True)

    # The id in that system, so we can find it again.
    external_id: Mapped[str] = mapped_column(String(512))

    title: Mapped[str] = mapped_column(String(1024))

    # Hash of the content: if it changes, we re-index only this document.
    content_hash: Mapped[str] = mapped_column(String(64), index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
