"""All database access for documents. No HTTP code here."""

import hashlib
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from erag.db.models.document import Document


def hash_content(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


async def get_by_id(session: AsyncSession, document_id: uuid.UUID) -> Document | None:
    return await session.get(Document, document_id)


async def get_by_external(
    session: AsyncSession, source: str, external_id: str
) -> Document | None:

    stmt = select(Document).where(
        Document.source == source, Document.external_id == external_id
    )

    return (await session.execute(stmt)).scalar_one_or_none()


async def upsert(
    session: AsyncSession, source: str, external_id: str, title: str, content: str
) -> tuple[Document, bool]:

    content_hash = hash_content(content)

    existing = await get_by_external(session, source, external_id)

    if existing is None:
        document = Document(
            source=source,
            external_id=external_id,
            title=title,
            content_hash=content_hash,
        )
        session.add(document)
        await session.commit()
        return document, True

    # Same content: nothing to do. This is what avoids a full re-index.
    if existing.content_hash == content_hash:
        return existing, False

    existing.title = title
    existing.content_hash = content_hash
    await session.commit()
    return existing, True
