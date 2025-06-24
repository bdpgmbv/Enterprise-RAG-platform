import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from erag.api.dependencies.auth import AdminPrincipal, CurrentPrincipal
from erag.api.errors import DocumentNotFoundError
from erag.api.schemas.document import DocumentCreate, DocumentRead
from erag.db.repositories import document as repo
from erag.db.session import get_session

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])


SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.post("", response_model=DocumentRead)
async def create_document(
    body: DocumentCreate,
    response: Response,
    session: SessionDep,
    principal: AdminPrincipal,
) -> DocumentRead:

    document, changed = await repo.upsert(
        session,
        body.source,
        body.external_id,
        body.title,
        body.content,
        body.allowed_groups,
    )

    response.status_code = status.HTTP_201_CREATED if changed else status.HTTP_200_OK

    log.info(
        "document_upserted",
        document_id=str(document.id),
        changed=changed,
        subject=principal.subject,
    )

    return DocumentRead.model_validate(document)


@router.get("/{document_id}", response_model=DocumentRead)
async def read_document(
    document_id: uuid.UUID,
    session: SessionDep,
    principal: CurrentPrincipal,
) -> DocumentRead:

    document = await repo.get_readable(session, document_id, principal.groups)

    await repo.record_access(
        session, principal.subject, document_id, allowed=document is not None
    )

    if document is None:
        raise DocumentNotFoundError(f"No document with id {document_id}")

    return DocumentRead.model_validate(document)
