import hashlib
import uuid
from collections.abc import Iterable

from sqlalchemy import delete, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from erag.db.models.access_log import AccessLog
from erag.db.models.document import Document
from erag.db.models.document_acl import DocumentAcl


def hash_content(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


async def get_by_external(
    session: AsyncSession, source: str, external_id: str
) -> Document | None:

    stmt = select(Document).where(
        Document.source == source, Document.external_id == external_id
    )

    return (await session.execute(stmt)).scalar_one_or_none()


async def upsert(
    session: AsyncSession,
    source: str,
    external_id: str,
    title: str,
    content: str,
    allowed_groups: Iterable[str],
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

        await session.flush()

        await set_acls(session, document.id, allowed_groups)

        await session.commit()

        return document, True

    await set_acls(session, existing.id, allowed_groups)

    if existing.content_hash == content_hash:
        await session.commit()
        return existing, False

    existing.title = title
    existing.content_hash = content_hash
    await session.commit()

    return existing, True


async def get_readable(
    session: AsyncSession, document_id: uuid.UUID, groups: Iterable[str]
) -> Document | None:

    allowed = exists().where(
        DocumentAcl.document_id == Document.id,
        DocumentAcl.group_name.in_(list(groups)),
    )

    stmt = select(Document).where(Document.id == document_id, allowed)

    return (await session.execute(stmt)).scalar_one_or_none()


async def set_acls(
    session: AsyncSession, document_id: uuid.UUID, groups: Iterable[str]
) -> None:
    await session.execute(
        delete(DocumentAcl).where(DocumentAcl.document_id == document_id)
    )
    session.add_all(
        DocumentAcl(document_id=document_id, group_name=g) for g in set(groups)
    )


async def record_access(
    session: AsyncSession, subject: str, document_id: uuid.UUID, allowed: bool
) -> None:
    session.add(AccessLog(subject=subject, document_id=document_id, allowed=allowed))
    await session.commit()
