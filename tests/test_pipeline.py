"""V0 tests: the ingestion contract.

Run with pytest, or standalone with no test dependencies at all:

    pytest -q
    python tests/test_pipeline.py

Tests that need chromadb and sentence-transformers are skipped when those are
not installed, so the ingestion contract stays verifiable on a bare checkout.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rag.chunker import Chunk, chunk_pages, split_sections  # noqa: E402
from rag.config import CHUNK_OVERLAP, CHUNK_SIZE, MIN_CHUNK_CHARS  # noqa: E402
from rag.golden import IN_SCOPE  # noqa: E402
from rag.loader import (  # noqa: E402
    Page,
    detect_heading,
    load_directory,
    load_document,
)

SAMPLE_DOCS = ROOT / "sample_docs"


def _pages() -> list[Page]:
    return load_directory(SAMPLE_DOCS)


def _chunks() -> list[Chunk]:
    return chunk_pages(_pages())


# --- loader ---------------------------------------------------------------


def test_sample_documents_exist() -> None:
    pdfs = sorted(SAMPLE_DOCS.glob("*.pdf"))
    assert len(pdfs) >= 2, "run `python scripts/make_sample_docs.py` first"


def test_every_page_carries_source_and_page_number() -> None:
    for page in _pages():
        assert page.source.endswith(".pdf")
        assert page.page >= 1, "page numbers are 1-indexed, matching a PDF reader"
        assert page.text.strip()


def test_page_numbers_are_unique_and_ascending_per_document() -> None:
    seen: dict[str, list[int]] = {}
    for page in _pages():
        seen.setdefault(page.source, []).append(page.page)
    for source, numbers in seen.items():
        assert numbers == sorted(numbers), f"{source} pages out of order"
        assert len(numbers) == len(set(numbers)), f"{source} has duplicate page numbers"


def test_running_footer_is_stripped_from_body_text() -> None:
    # The generated PDFs carry a footer on every page. It must not survive into
    # page text, or it lands in every chunk and dilutes every embedding.
    footer_fragment = "Internal Operations Document"
    leaked = [
        p.page
        for p in _pages()
        if p.source.startswith("Global") and footer_fragment in p.text
    ]
    assert not leaked, f"footer leaked into pages {leaked}"


def test_page_labels_are_stripped() -> None:
    for page in _pages():
        for line in page.text.split("\n"):
            assert line.strip().lower() != f"page {page.page}"


def test_unsupported_file_type_is_rejected() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        unsupported = Path(directory) / "contract.docx"
        unsupported.write_bytes(b"not a pdf")
        try:
            load_document(unsupported)
        except ValueError:
            return
    raise AssertionError("expected ValueError for an unsupported extension")


def test_directory_loader_ignores_unsupported_files() -> None:
    import shutil
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory)
        shutil.copy(sorted(SAMPLE_DOCS.glob("*.pdf"))[0], target)
        (target / "notes.docx").write_bytes(b"ignore me")
        pages = load_directory(target)
        assert pages, "the PDF should still load"
        assert {p.source for p in pages} == {sorted(SAMPLE_DOCS.glob("*.pdf"))[0].name}


# --- heading detection ----------------------------------------------------


def test_detect_heading_accepts_real_headings() -> None:
    assert detect_heading("4.2 Temperature Deviation and Weekend Escalation")
    assert detect_heading("7 Customer Communication Standards")
    assert detect_heading("Appendix A — Controlled Forms Register")


def test_detect_heading_rejects_wrapped_body_lines() -> None:
    # Body text that happens to start with a number is the failure mode that
    # would mislabel citations, so it is pinned here.
    assert detect_heading("30 calendar days from the invoice date, extended to") is None
    assert detect_heading("2°C from the contracted set point") is None
    assert detect_heading("Page 7") is None
    assert detect_heading("") is None


# --- chunker --------------------------------------------------------------


def test_every_chunk_has_the_required_metadata() -> None:
    for chunk in _chunks():
        metadata = chunk.metadata()
        for key in ("source", "page", "chunk_id"):
            assert key in metadata, f"{chunk.id} is missing {key}"
            assert metadata[key] != "" and metadata[key] is not None


def test_no_metadata_value_is_none() -> None:
    # Chroma rejects None metadata values; an empty string is the sentinel.
    for chunk in _chunks():
        for key, value in chunk.metadata().items():
            assert value is not None, f"{chunk.id}.{key} is None"
            assert isinstance(value, (str, int, float, bool))


def test_chunk_ids_are_unique_and_deterministic() -> None:
    first = _chunks()
    second = _chunks()
    ids = [c.id for c in first]
    assert len(ids) == len(set(ids)), "duplicate chunk ids would silently overwrite"
    assert ids == [c.id for c in second], "ids must be stable across runs for upsert"


def test_chunk_id_restarts_per_page() -> None:
    by_page: dict[tuple[str, int], list[int]] = {}
    for chunk in _chunks():
        by_page.setdefault((chunk.source, chunk.page), []).append(chunk.chunk_id)
    for key, values in by_page.items():
        assert values == list(range(len(values))), f"{key} chunk_ids are not 0..n"


def test_chunks_respect_the_configured_size() -> None:
    limit = CHUNK_SIZE + CHUNK_OVERLAP  # overlap is prepended to each piece
    for chunk in _chunks():
        assert len(chunk.text) <= limit, f"{chunk.id} is {len(chunk.text)} chars"
        assert len(chunk.text) >= MIN_CHUNK_CHARS


def test_overlap_carries_context_between_adjacent_chunks() -> None:
    page = Page(
        source="synthetic.pdf",
        page=1,
        text="9 Section Nine\n" + " ".join(f"word{i}" for i in range(1200)),
    )
    chunks = chunk_page_helper(page)
    assert len(chunks) > 1, "test text should be long enough to split"
    for previous, current in zip(chunks, chunks[1:]):
        tail_words = previous.text.split()[-8:]
        assert any(word in current.text for word in tail_words), (
            "adjacent chunks share no words — a sentence on the boundary would "
            "be retrievable from neither side"
        )


def chunk_page_helper(page: Page) -> list[Chunk]:
    from rag.chunker import chunk_page

    return chunk_page(page)


def test_a_chunk_never_spans_two_sections() -> None:
    # The whole value of the product is a citation you can trust. If a chunk
    # covered two subsections, its section label would be wrong for half of it.
    for chunk in _chunks():
        headings = {
            detect_heading(line)
            for line in chunk.text.split("\n")
            if detect_heading(line)
        }
        assert len(headings) <= 1, f"{chunk.id} contains headings {headings}"
        if headings and chunk.section:
            assert headings == {chunk.section}


def test_split_sections_attributes_body_to_its_own_heading() -> None:
    text = "3 Alpha\nbody of alpha\n3.1 Beta\nbody of beta"
    segments = split_sections(text)
    assert [s for s, _ in segments] == ["3 Alpha", "3.1 Beta"]
    assert "body of beta" in segments[1][1]


def test_text_above_a_heading_is_not_labelled_with_it() -> None:
    # A page opens with the continuation of the previous page's section. That
    # text must not inherit a heading that appears further down the page.
    page = Page(
        source="synthetic.pdf",
        page=2,
        text="continuation text from the previous page, long enough to keep\n"
        "5 New Section\nbody of the new section here",
        section="5 New Section",
        opening_section="4.9 Previous Section",
    )
    chunks = chunk_page_helper(page)
    assert chunks[0].section == "4.9 Previous Section"
    assert chunks[-1].section == "5 New Section"


# --- golden set (chunk level) --------------------------------------------


def test_every_golden_answer_survives_chunking() -> None:
    """Before blaming the embedding model, prove the answer is in the corpus.

    A retrieval miss has two causes: the answer never made it into a chunk, or
    the embedding did not rank it. This test rules out the first, so a failure
    in verify_v0.py can only mean the second.
    """
    chunks = _chunks()
    failures: list[str] = []
    for question in IN_SCOPE:
        matches = [
            c
            for c in chunks
            if c.source == question.expect_source
            and all(p.lower() in c.text.lower() for p in question.expect_phrases)
            and c.page in question.expect_pages
        ]
        if not matches:
            failures.append(f"{question.question!r} -> no chunk on page(s) {question.expect_pages}")
        elif question.expect_section_prefix:
            sections = {m.section or "" for m in matches}
            if not any(s.startswith(question.expect_section_prefix) for s in sections):
                failures.append(
                    f"{question.question!r} -> expected section "
                    f"{question.expect_section_prefix}, got {sorted(sections)}"
                )
    assert not failures, "\n".join(failures)


# --- vector store (skipped without the heavy dependencies) ---------------


def _chromadb_available() -> bool:
    try:
        import chromadb  # noqa: F401

        return True
    except ImportError:
        return False


class _StubEmbedder:
    """Deterministic bag-of-characters vectors — no model download required."""

    dimensions = 64

    def encode(self, texts):  # type: ignore[no-untyped-def]
        vectors = []
        for text in texts:
            vector = [0.0] * self.dimensions
            for character in text.lower():
                vector[ord(character) % self.dimensions] += 1.0
            norm = sum(v * v for v in vector) ** 0.5 or 1.0
            vectors.append([v / norm for v in vector])
        return vectors


def test_vector_store_roundtrip_preserves_metadata(tmp_path=None) -> None:
    if not _chromadb_available():
        print("      (skipped: chromadb not installed)")
        return
    import tempfile

    from rag.vector_store import VectorStore

    directory = tmp_path or Path(tempfile.mkdtemp())
    store = VectorStore(
        persist_dir=directory / "chroma",
        collection_name="test_roundtrip",
        embedder=_StubEmbedder(),
    )
    store.reset()
    chunks = _chunks()[:20]
    assert store.add_chunks(chunks) == len(chunks)
    assert store.count() == len(chunks)

    results = store.query("temperature deviation weekend escalation", top_k=3)
    assert results, "query returned nothing"
    for hit in results:
        assert hit.source and hit.page >= 1
        assert 0.0 <= hit.score <= 1.0


def test_vector_store_rejects_chunks_without_metadata() -> None:
    if not _chromadb_available():
        print("      (skipped: chromadb not installed)")
        return
    import tempfile

    from rag.vector_store import VectorStore

    store = VectorStore(
        persist_dir=Path(tempfile.mkdtemp()) / "chroma",
        collection_name="test_guard",
        embedder=_StubEmbedder(),
    )
    bad = Chunk(text="a chunk with no source at all", source="", page=1, chunk_id=0)
    try:
        store.add_chunks([bad])
    except ValueError:
        return
    raise AssertionError("expected ValueError for a chunk with no source")


# --- standalone runner ----------------------------------------------------


def _main() -> int:
    tests = [
        (name, obj)
        for name, obj in sorted(globals().items())
        if name.startswith("test_") and callable(obj)
    ]
    failed = 0
    for name, test in tests:
        try:
            test()
        except AssertionError as error:
            failed += 1
            print(f"FAIL  {name}\n      {error}")
        except Exception as error:  # noqa: BLE001
            failed += 1
            print(f"ERROR {name}\n      {type(error).__name__}: {error}")
        else:
            print(f"pass  {name}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_main())
