"""Page-aware document loading.

INVARIANT: text never leaves this module without the page number it came from.
An answer without a page citation is a bug, and extraction time is the only
place a page number can be established.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable, Sequence

from pypdf import PdfReader

SUPPORTED_SUFFIXES = {".pdf", ".md", ".txt"}

# A heading looks like "4.2 Temperature Deviation" or "Appendix B — Rota".
# The title must start with a capital and carry no sentence punctuation, which
# is what keeps wrapped body lines such as "30 calendar days from the invoice
# date, extended to" from being mistaken for headings.
_HEADING_RE = re.compile(r"^(?P<num>\d+(?:\.\d+)*)\s+(?P<title>[A-Z][^.,;:]{2,70})$")
_APPENDIX_RE = re.compile(
    r"^(?P<num>Appendix(?:\s+[A-Z])?)\s*[—–-]?\s*(?P<title>[^.,;:]{0,70})$"
)
# Running footers extracted by pypdf arrive as short lines like "Page 7".
_PAGE_LABEL_RE = re.compile(r"^(?:page\s*)?\d{1,4}\s*(?:of\s*\d{1,4})?$", re.IGNORECASE)

MAX_HEADING_LEN = 90


def detect_heading(line: str) -> str | None:
    """Return a normalised heading for this line, or None if it isn't one."""
    line = line.strip()
    if not line or len(line) > MAX_HEADING_LEN:
        return None
    match = _HEADING_RE.match(line)
    if match:
        return f"{match.group('num')} {match.group('title').strip()}".strip()
    match = _APPENDIX_RE.match(line)
    if match:
        title = match.group("title").strip()
        return f"{match.group('num')} {title}".strip() if title else match.group("num")
    return None


@dataclass(frozen=True)
class Page:
    """One page of one source document."""

    source: str  # filename only, e.g. "Operations_SOP.pdf"
    page: int  # 1-indexed, matching what a human sees in a PDF reader
    text: str
    section: str | None = None  # last heading in force on this page
    opening_section: str | None = None  # section in force at the top of the page

    @property
    def citation(self) -> str:
        base = f"{self.source}, Page {self.page}"
        return f"{base}, Section {self.section}" if self.section else base


def _clean(text: str) -> str:
    """Normalise whitespace without destroying paragraph boundaries."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Repair words hyphenated across a line break: "esca-\nlation" -> "escalation".
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _last_heading(text: str) -> str | None:
    """The last heading on a page — the section a chunk at the page foot belongs to."""
    found: str | None = None
    for line in text.split("\n"):
        heading = detect_heading(line)
        if heading:
            found = heading
    return found


def _boilerplate_lines(
    page_texts: Sequence[str], threshold: float = 0.6, max_len: int = 140
) -> set[str]:
    """Find running headers/footers: short lines repeated across most pages.

    pypdf returns canvas-drawn footers as ordinary text, so without this the
    string "Northwind Freight Group — Revision 4.1" lands in every chunk and
    dilutes every one of their embeddings. Detecting repetition rather than
    matching known strings matters because client documents arrive with
    footers nobody has seen before.
    """
    if len(page_texts) < 3:
        return set()
    counts: Counter[str] = Counter()
    for text in page_texts:
        counts.update(
            {
                line.strip()
                for line in text.split("\n")
                if line.strip() and len(line.strip()) <= max_len
            }
        )
    total = len(page_texts)
    return {line for line, count in counts.items() if count / total >= threshold}


def _strip_boilerplate(text: str, boilerplate: set[str]) -> str:
    kept = [
        line
        for line in text.split("\n")
        if line.strip() not in boilerplate and not _PAGE_LABEL_RE.match(line.strip())
    ]
    return _clean("\n".join(kept))


def _resolve_sections(pages: list[Page]) -> list[Page]:
    """Resolve each page's opening and closing section.

    Two labels are needed, not one. `opening_section` is what is in force at the
    top of the page — a subsection running across a page break has its heading
    on the earlier page, so the continuation page must inherit it. `section` is
    the last heading in force anywhere on the page, which is the right label for
    a page-level citation. Passing the page's own last heading down to text that
    appears *above* it would mislabel the top of every page.
    """
    resolved: list[Page] = []
    carried: str | None = None
    for page in pages:
        own_last = page.section  # set by the loader to this page's last heading
        resolved.append(
            replace(page, section=own_last or carried, opening_section=carried)
        )
        carried = own_last or carried
    return resolved


def load_pdf(path: str | Path) -> list[Page]:
    """Extract a PDF page by page, attaching a 1-indexed page number to each."""
    path = Path(path)
    reader = PdfReader(str(path))

    # Pass 1: raw text per page, so repeated headers/footers can be spotted.
    raw_texts = [_clean(page.extract_text() or "") for page in reader.pages]
    boilerplate = _boilerplate_lines(raw_texts)

    # Pass 2: build Pages from de-boilerplated text. Page numbers come from the
    # enumeration, so skipping a blank page never shifts the ones after it.
    pages: list[Page] = []
    for index, raw_text in enumerate(raw_texts, start=1):
        text = _strip_boilerplate(raw_text, boilerplate)
        if not text:
            # Blank or image-only page. Skipped deliberately: OCR is a V2
            # concern, and an empty chunk would only pollute retrieval.
            continue
        pages.append(
            Page(source=path.name, page=index, text=text, section=_last_heading(text))
        )
    return _resolve_sections(pages)


def load_text_file(path: str | Path, chars_per_page: int = 3000) -> list[Page]:
    """Load .md/.txt by splitting into pseudo-pages on paragraph boundaries.

    Plain text has no pages, but the citation contract requires a page number,
    so stable ones are synthesised. Splits fall only between paragraphs, so a
    cited passage is never cut mid-sentence.
    """
    path = Path(path)
    text = _clean(path.read_text(encoding="utf-8", errors="replace"))
    paragraphs = [p for p in text.split("\n\n") if p.strip()]

    pages: list[Page] = []
    buffer: list[str] = []
    size = 0

    def flush() -> None:
        nonlocal buffer, size
        if not buffer:
            return
        body = "\n\n".join(buffer)
        pages.append(
            Page(
                source=path.name,
                page=len(pages) + 1,
                text=body,
                section=_last_heading(body),
            )
        )
        buffer, size = [], 0

    for paragraph in paragraphs:
        if size and size + len(paragraph) > chars_per_page:
            flush()
        buffer.append(paragraph)
        size += len(paragraph) + 2
    flush()
    return _resolve_sections(pages)


def load_document(path: str | Path) -> list[Page]:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return load_pdf(path)
    if suffix in {".md", ".txt"}:
        return load_text_file(path)
    raise ValueError(
        f"Unsupported file type: {path.name} (supported: {sorted(SUPPORTED_SUFFIXES)})"
    )


def load_directory(directory: str | Path) -> list[Page]:
    """Load every supported document in a directory, sorted for reproducibility."""
    directory = Path(directory)
    if not directory.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")
    pages: list[Page] = []
    for path in sorted(directory.iterdir()):
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
            pages.extend(load_document(path))
    return pages


def summarise(pages: Iterable[Page]) -> str:
    counts: dict[str, int] = {}
    for page in pages:
        counts[page.source] = counts.get(page.source, 0) + 1
    return ", ".join(f"{name} ({n} pages)" for name, n in sorted(counts.items()))
