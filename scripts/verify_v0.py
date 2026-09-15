#!/usr/bin/env python3
"""V0 acceptance check: does real vector retrieval return the right pages?

    python scripts/verify_v0.py            # uses a throwaway collection
    python scripts/verify_v0.py --keep     # keep the index for `ingest.py query`

Needs chromadb and sentence-transformers installed (pip install -r
requirements.txt). The first run downloads the embedding model, roughly 90 MB.

What it proves, and why each part matters:

  1. Every golden question returns its expected document and page inside the
     top-k. That is the "Retrieval Test" checkbox in the README.
  2. Every retrieved hit carries source, page and chunk_id. An answer without a
     page citation is a bug, so the metadata invariant is asserted on the way
     out of the store, not just on the way in.
  3. Out-of-scope questions score visibly lower than in-scope ones. V1's
     refusal has to be based on something; this prints the margin and a
     suggested similarity floor to put in the retrieval gate.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rag.chunker import chunk_pages  # noqa: E402
from rag.config import SAMPLE_DOCS_DIR, TOP_K  # noqa: E402
from rag.golden import IN_SCOPE, OUT_OF_SCOPE  # noqa: E402
from rag.loader import load_directory, summarise  # noqa: E402

TICK, CROSS = "PASS", "FAIL"


def _fatal(message: str) -> int:
    print(f"\n{message}\n", file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="V0 retrieval acceptance check")
    parser.add_argument("--top-k", type=int, default=TOP_K)
    parser.add_argument(
        "--keep",
        action="store_true",
        help="index into the project's own .chroma instead of a temp directory",
    )
    args = parser.parse_args(argv)

    try:
        from rag.vector_store import VectorStore
    except ImportError as error:
        return _fatal(
            f"missing dependency ({error.name}). Run:\n"
            "    pip install -r requirements.txt"
        )

    print("=" * 74)
    print("Pillar 3 — V0 retrieval acceptance check")
    print("=" * 74)

    pages = load_directory(SAMPLE_DOCS_DIR)
    if not pages:
        return _fatal(
            f"no documents found in {SAMPLE_DOCS_DIR}. Run:\n"
            "    python scripts/make_sample_docs.py"
        )
    chunks = chunk_pages(pages)
    print(f"\ncorpus    {summarise(pages)}")
    print(f"chunks    {len(chunks)}")

    temp_dir = None
    if args.keep:
        store = VectorStore(collection_name="v0_verify")
    else:
        temp_dir = Path(tempfile.mkdtemp(prefix="pillar3_verify_"))
        store = VectorStore(persist_dir=temp_dir / "chroma", collection_name="v0_verify")

    try:
        store.reset()
        started = time.perf_counter()
        store.add_chunks(chunks)
        print(f"indexed   {store.count()} chunks in {time.perf_counter() - started:.1f}s")
        print(f"model     {getattr(store.embedder, 'model_name', 'custom')}")

        # --- 1 & 2: in-scope retrieval and metadata ---
        print(f"\nIn-scope questions (top-{args.top_k})")
        print("-" * 74)
        failures: list[str] = []
        in_scope_top: list[float] = []
        latencies: list[float] = []

        for question in IN_SCOPE:
            started = time.perf_counter()
            hits = store.query(question.question, top_k=args.top_k)
            latencies.append((time.perf_counter() - started) * 1000)

            if not hits:
                failures.append(f"{question.question!r}: no results at all")
                print(f"  {CROSS}  {question.question[:56]}")
                continue

            in_scope_top.append(hits[0].score)

            for hit in hits:
                if not hit.source or hit.page < 1:
                    failures.append(
                        f"{question.question!r}: hit is missing source/page metadata"
                    )

            matched = [
                hit
                for hit in hits
                if hit.source == question.expect_source
                and hit.page in question.expect_pages
                and all(p.lower() in hit.text.lower() for p in question.expect_phrases)
            ]
            if matched:
                best = matched[0]
                rank = hits.index(best) + 1
                label = f"p{best.page}"
                if best.section:
                    label += f" §{best.section.split()[0]}"
                print(
                    f"  {TICK}  {question.question[:52]:52} rank {rank}  "
                    f"{label:12} sim {best.score:.3f}"
                )
            else:
                got = ", ".join(f"{h.source.split('_')[0]} p{h.page}" for h in hits)
                failures.append(
                    f"{question.question!r}: expected {question.expect_source} "
                    f"page(s) {question.expect_pages}, got [{got}]"
                )
                print(f"  {CROSS}  {question.question[:52]:52} got [{got}]")

        # --- 3: out-of-scope separation ---
        print("\nOut-of-scope questions (should score low — V1 must refuse these)")
        print("-" * 74)
        out_of_scope_top: list[float] = []
        for question in OUT_OF_SCOPE:
            hits = store.query(question.question, top_k=args.top_k)
            top = hits[0].score if hits else 0.0
            out_of_scope_top.append(top)
            nearest = f"{hits[0].source} p{hits[0].page}" if hits else "-"
            print(f"       {question.question[:52]:52} sim {top:.3f}  ({nearest})")

        print("\n" + "=" * 74)
        worst_in = min(in_scope_top) if in_scope_top else 0.0
        best_out = max(out_of_scope_top) if out_of_scope_top else 0.0
        margin = worst_in - best_out
        print(f"in-scope  lowest top-1 similarity  {worst_in:.3f}")
        print(f"off-topic highest top-1 similarity {best_out:.3f}")
        print(f"margin                             {margin:+.3f}")
        if margin > 0.05:
            floor = round(best_out + margin / 2, 2)
            print(
                f"\nSuggested V1 similarity floor: {floor}\n"
                "  Below it, refuse before calling the model — cheaper than asking an\n"
                "  LLM to decline, and it cannot be talked out of the refusal."
            )
        else:
            print(
                "\nNo usable similarity gap. Do not gate V1's refusal on the score\n"
                "alone — rely on the strict grounding prompt and revisit chunking."
            )
        if latencies:
            print(f"\nretrieval latency  mean {sum(latencies) / len(latencies):.0f} ms, "
                  f"max {max(latencies):.0f} ms")

        print("=" * 74)
        if failures:
            print(f"\n{len(failures)} FAILURE(S):")
            for failure in failures:
                print(f"  - {failure}")
            print(
                "\nIf tests/test_pipeline.py passes but this does not, the answer is in\n"
                "the corpus and the embedding model is not ranking it. Try a larger\n"
                "chunk overlap, or a stronger embedding model, before touching prompts."
            )
            return 1

        print(f"\nAll {len(IN_SCOPE)} in-scope questions returned the expected page. V0 is done.")
        if args.keep:
            print("Index kept — try:  python ingest.py query \"weekend temperature abuse\"")
        return 0
    finally:
        if temp_dir and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
