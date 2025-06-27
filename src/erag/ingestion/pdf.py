from dataclasses import dataclass
from pathlib import Path

import pdfplumber


@dataclass(frozen=True)
class Page:
    """One page of a document. The number is what citations point at."""

    number: int
    text: str


def parse_pdf(path: Path) -> list[Page]:
    """Read a PDF into pages, keeping the page number with the text."""
    pages: list[Page] = []

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = (page.extract_text() or "").strip()
            if text:
                pages.append(Page(number=page.page_number, text=text))

    return pages