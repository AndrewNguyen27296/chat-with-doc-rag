"""Pillar 3 RAG engine: page-aware ingestion, chunking, and local vector search.

`VectorStore` is exported lazily so that importing `rag` — or using the loader
and chunker alone — does not pull in chromadb and sentence-transformers. Those
are heavy, and ingestion tooling should stay usable without them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rag.chunker import Chunk, chunk_page, chunk_pages
from rag.loader import Page, load_directory, load_document, load_pdf

if TYPE_CHECKING:  # pragma: no cover
    from rag.vector_store import Retrieved, VectorStore

__all__ = [
    "Page",
    "load_pdf",
    "load_document",
    "load_directory",
    "Chunk",
    "chunk_page",
    "chunk_pages",
    "VectorStore",
    "Retrieved",
]

_LAZY = {"VectorStore": "rag.vector_store", "Retrieved": "rag.vector_store"}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        from importlib import import_module

        return getattr(import_module(_LAZY[name]), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
