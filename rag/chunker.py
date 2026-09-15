"""Recursive character chunking with overlap, aligned to document sections.

INVARIANT: every chunk carries {"source", "page", "chunk_id"}. Metadata is
built here and never reconstructed downstream.

Chunks are cut at section boundaries first, then split down to size. That means
a chunk never straddles two subsections, so the section label on a citation is
always the section the quoted text actually came from — which is the difference
between citing "Page 4" and citing "Page 4, Section 4.2".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from rag.config import CHUNK_OVERLAP, CHUNK_SIZE, MIN_CHUNK_CHARS
from rag.loader import Page, detect_heading

# Tried in order: split on the strongest boundary that yields small-enough
# pieces, so chunks break between paragraphs before they break mid-word.
SEPARATORS: Sequence[str] = ("\n\n", "\n", ". ", "; ", ", ", " ", "")


@dataclass(frozen=True)
class Chunk:
    text: str
    source: str
    page: int
    chunk_id: int
    section: str | None = None

    @property
    def id(self) -> str:
        """Stable, collision-free id, so re-ingesting a document upserts cleanly."""
        return f"{self.source}::p{self.page}::c{self.chunk_id}"

    @property
    def citation(self) -> str:
        base = f"{self.source}, Page {self.page}"
        return f"{base}, Section {self.section}" if self.section else base

    def metadata(self) -> dict[str, object]:
        # Chroma metadata values must be str/int/float/bool — never None.
        return {
            "source": self.source,
            "page": self.page,
            "chunk_id": self.chunk_id,
            "section": self.section or "",
            "citation": self.citation,
        }


def split_sections(text: str, fallback: str | None = None) -> list[tuple[str | None, str]]:
    """Split page text into (section, body) segments at heading lines.

    The heading line stays at the top of its own segment: it is real retrievable
    text ("Weekend Escalation" is exactly what someone would search for), and
    keeping it also makes the citation drawer excerpt self-explanatory.
    """
    segments: list[tuple[str | None, str]] = []
    current: str | None = fallback
    buffer: list[str] = []

    for line in text.split("\n"):
        heading = detect_heading(line)
        if heading:
            if buffer:
                segments.append((current, "\n".join(buffer)))
            current = heading
            buffer = [line.strip()]
        else:
            buffer.append(line)
    if buffer:
        segments.append((current, "\n".join(buffer)))

    return [(section, body) for section, body in segments if body.strip()]


def _split_recursive(text: str, chunk_size: int, separators: Sequence[str]) -> list[str]:
    """Split text into pieces of at most chunk_size, preferring strong boundaries."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    separator, *rest = separators
    if separator == "":
        # Last resort: a hard character slice.
        return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

    parts = text.split(separator)
    pieces: list[str] = []
    buffer = ""

    for part in parts:
        candidate = f"{buffer}{separator}{part}" if buffer else part
        if len(candidate) <= chunk_size:
            buffer = candidate
            continue
        if buffer:
            pieces.append(buffer)
        if len(part) > chunk_size:
            # This single part is still too long — recurse with a weaker separator.
            pieces.extend(_split_recursive(part, chunk_size, rest))
            buffer = ""
        else:
            buffer = part

    if buffer:
        pieces.append(buffer)
    return [p.strip() for p in pieces if p.strip()]


def _apply_overlap(pieces: list[str], overlap: int) -> list[str]:
    """Prefix each piece with the tail of its predecessor to keep continuity.

    A sentence straddling a boundary would otherwise be retrievable from
    neither side. The tail is trimmed to a word boundary so the overlap still
    reads cleanly when a client opens the citation drawer.
    """
    if overlap <= 0 or len(pieces) < 2:
        return pieces
    out = [pieces[0]]
    for previous, current in zip(pieces, pieces[1:]):
        tail = previous[-overlap:]
        if " " in tail:
            tail = tail.split(" ", 1)[1]
        out.append(f"{tail.strip()} {current}".strip())
    return out


def _is_heading_only(piece: str, section: str | None) -> bool:
    """True when a piece is just its heading, with no body worth embedding."""
    stripped = piece.strip()
    if section and stripped == section.strip():
        return True
    return len(stripped) < MIN_CHUNK_CHARS


def chunk_page(
    page: Page,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[Chunk]:
    """Chunk one page, section by section. chunk_id restarts at 0 on each page."""
    chunks: list[Chunk] = []
    next_id = 0

    for section, body in split_sections(page.text, fallback=page.opening_section):
        pieces = _apply_overlap(_split_recursive(body, chunk_size, SEPARATORS), overlap)
        for piece in pieces:
            if _is_heading_only(piece, section):
                # A bare heading stranded at the foot of a page carries no
                # answer. Its body lives on the next page, which inherits the
                # section label via Page.opening_section, so nothing is lost.
                continue
            chunks.append(
                Chunk(
                    text=piece,
                    source=page.source,
                    page=page.page,
                    chunk_id=next_id,
                    section=section,
                )
            )
            next_id += 1
    return chunks


def chunk_pages(
    pages: Iterable[Page],
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for page in pages:
        chunks.extend(chunk_page(page, chunk_size=chunk_size, overlap=overlap))
    return chunks
