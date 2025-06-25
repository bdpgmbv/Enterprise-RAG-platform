"""All ORM models. Alembic imports this to discover tables."""

from erag.db.models.document import Document

__all__ = ["Document"]
