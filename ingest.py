#!/usr/bin/env python3
"""V0 command line: index documents into the local vector store, then query it.

    python ingest.py index                    # index sample_docs/
    python ingest.py index --path ./my_docs --reset
    python ingest.py query "weekend temperature deviation on perishable cargo"
    python ingest.py query "dental co-pay cap" --source Employee_Handbook_2026.pdf
    python ingest.py stats

Retrieval only. Answer generation is V1 — this CLI proves that the right pages
come back, which is the thing that has to be true before an LLM sees anything.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from rag.chunker import chunk_pages
from rag.config import CHROMA_DIR, COLLECTION_NAME, SAMPLE_DOCS_DIR, TOP_K
from rag.loader import load_directory, load_document, summarise


def _store():
    # Imported lazily so `--help` and argument errors do not pay the cost of
    # loading chromadb and the embedding model.
    from rag.vector_store import VectorStore

    return VectorStore()


def cmd_index(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if not path.exists():
        print(f"error: {path} does not exist", file=sys.stderr)
        return 1

    started = time.perf_counter()
    pages = load_directory(path) if path.is_dir() else load_document(path)
    if not pages:
        print(f"error: no readable text found in {path}", file=sys.stderr)
        return 1
    print(f"loaded    {summarise(pages)}")

    chunks = chunk_pages(pages)
    sizes = [len(c.text) for c in chunks]
    print(
        f"chunked   {len(chunks)} chunks "
        f"({min(sizes)}-{max(sizes)} chars, mean {sum(sizes) // len(sizes)})"
    )

    store = _store()
    if args.reset:
        store.reset()
        print("reset     collection dropped and recreated")

    written = store.add_chunks(chunks)
    elapsed = time.perf_counter() - started
    print(f"indexed   {written} chunks into {CHROMA_DIR}/{COLLECTION_NAME}")
    print(f"total     {store.count()} chunks in collection ({elapsed:.1f}s)")
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    store = _store()
    if store.count() == 0:
        print("error: index is empty — run `python ingest.py index` first", file=sys.stderr)
        return 1

    started = time.perf_counter()
    results = store.query(args.question, top_k=args.top_k, source=args.source)
    elapsed = time.perf_counter() - started

    if not results:
        print("no matches")
        return 0

    print(f'\nQ: "{args.question}"   ({elapsed * 1000:.0f} ms)\n')
    for rank, hit in enumerate(results, start=1):
        excerpt = " ".join(hit.text.split())
        if len(excerpt) > 420:
            excerpt = excerpt[:420].rsplit(" ", 1)[0] + " …"
        print(f"  [{rank}] {hit.citation}")
        print(f"      similarity {hit.score:.3f}")
        print(f"      {excerpt}\n")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    store = _store()
    print(f"collection  {COLLECTION_NAME}")
    print(f"location    {CHROMA_DIR}")
    print(f"chunks      {store.count()}")
    sources = store.sources()
    print(f"documents   {len(sources)}")
    for name in sources:
        print(f"            - {name}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ingest.py", description="Pillar 3 V0: ingest documents and query them locally."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_index = sub.add_parser("index", help="load, chunk and index documents")
    p_index.add_argument(
        "--path", default=str(SAMPLE_DOCS_DIR), help="file or directory (default: sample_docs/)"
    )
    p_index.add_argument(
        "--reset", action="store_true", help="drop the collection before indexing"
    )
    p_index.set_defaults(func=cmd_index)

    p_query = sub.add_parser("query", help="retrieve the top matching chunks")
    p_query.add_argument("question")
    p_query.add_argument("--top-k", type=int, default=TOP_K)
    p_query.add_argument("--source", default=None, help="restrict to one filename")
    p_query.set_defaults(func=cmd_query)

    p_stats = sub.add_parser("stats", help="show what is currently indexed")
    p_stats.set_defaults(func=cmd_stats)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
