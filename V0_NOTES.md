# V0 — The Vector Search Engine

Built and verified 2026-09-08. Retrieval only: no LLM call anywhere in this
phase, on purpose. The question V0 answers is *"do the right pages come back?"*
— because if they don't, no prompt in V1 can save the demo.

## Run it

```bash
python -m venv .venv && .venv\Scripts\activate     # Windows
pip install -r requirements.txt                     # ~1 min; first embed downloads ~90 MB

python scripts/verify_v0.py                         # the acceptance check — start here
python ingest.py index --reset                      # index sample_docs/ into .chroma
python ingest.py query "weekend temperature abuse on perishable cargo"
python ingest.py stats
```

Tests need nothing beyond `pypdf`:

```bash
python tests/test_pipeline.py     # or: pytest -q
```

## What's in here

| Path | Does |
| :--- | :--- |
| `rag/loader.py` | Page-by-page PDF extraction. Attaches a 1-indexed page number to every slice, strips running headers/footers by detecting lines repeated across pages, repairs hyphens broken across line ends, and resolves each page's opening and closing section. |
| `rag/chunker.py` | Cuts at section boundaries first, then recursively down to ~500 tokens with 50-token overlap. Builds `{source, page, chunk_id, section, citation}` on every chunk. |
| `rag/vector_store.py` | Local persistent ChromaDB, cosine space, `all-MiniLM-L6-v2` embeddings. Upserts on stable ids, and *refuses* to index a chunk with incomplete metadata. |
| `rag/golden.py` | The acceptance question set — expected document, page, section and phrase for each, plus deliberate out-of-scope questions. |
| `ingest.py` | `index` / `query` / `stats` CLI. |
| `scripts/make_sample_docs.py` | Regenerates the two sample handbooks from `sample_content.py`. |
| `scripts/verify_v0.py` | End-to-end acceptance check against `rag/golden.py`. |

## Design decisions worth knowing

**Chunks are cut at section boundaries before they're cut to size.** A chunk
never straddles two subsections, so a citation reads `Page 4, Section 4.2
Temperature Deviation and Weekend Escalation` rather than just `Page 4`.
Subsection-level citation is the demo's whole selling point, and it's only
trustworthy if a chunk can't span two sections. `test_a_chunk_never_spans_two_sections`
pins that.

**Two section labels per page, not one.** `Page.section` is the last heading in
force on the page (right for a page-level citation); `Page.opening_section` is
what's in force at the top (right for text continuing from the previous page).
Using one label for both mislabels the top of every page.

**Running footers are detected, not hard-coded.** `pypdf` returns canvas-drawn
footers as ordinary text. Left alone, "Northwind Freight Group — Revision 4.1"
lands in all 57 chunks and dilutes every embedding. Lines repeated across ≥60%
of pages are dropped — client documents will have footers nobody has seen.

**Blank pages are skipped without shifting page numbers.** Page numbers come
from the enumeration of the raw PDF, so a skipped image-only page never
silently renumbers the pages after it.

**Heading detection rejects wrapped body lines.** A body line like `"30 calendar
days from the invoice date, extended to"` looks exactly like a numbered
heading. Requiring a capitalised title with no sentence punctuation is what
keeps citations from being mislabelled; `test_detect_heading_rejects_wrapped_body_lines`
pins the specific failure cases.

**The embedder is injected, not imported.** `VectorStore` takes an `Embedder`
protocol, so the store is testable without downloading a model and swapping
MiniLM for a hosted embedding model later touches one class.

**`import rag` doesn't pull in chromadb.** `VectorStore` is exported lazily, so
loader/chunker tooling runs on a bare checkout.

## Verification status

Run on the sample corpus: **18 pages → 57 chunks**, 70–1354 chars, mean 394.

- `tests/test_pipeline.py` — **21/21 passing.** Covers page-number integrity,
  footer stripping, metadata completeness, no-None metadata (Chroma rejects it),
  id uniqueness and determinism, chunk-size bounds, overlap continuity,
  section purity, and section inheritance across page breaks.
- `test_every_golden_answer_survives_chunking` — **passing.** Every golden
  answer is present in a chunk on its expected page and section. This separates
  the two causes of a retrieval miss: if this passes and `verify_v0.py` fails,
  the answer is in the corpus and the *embedding* isn't ranking it.
- Ranking sanity check — all 7 in-scope questions came back **rank 1**, and both
  out-of-scope questions scored **0.000**, under a TF-IDF ranker standing in for
  the embedding model.

**Superseded — see `V1_NOTES.md` for current status.** `scripts/verify_v0.py`
has since been run against real ChromaDB 1.5.9: **7/7 golden questions at rank 1**
with the correct page and section, mean 8 ms. It has still *not* been run with
all-MiniLM-L6-v2 — `huggingface.co` and `download.pytorch.org` are blocked by
egress policy in the build environment, so a TF-IDF stand-in embedder was
substituted. Run it once on a machine with normal internet to confirm the
embedding ranking and to get a real similarity floor for `SIMILARITY_FLOOR`.

## Known limits (deliberate, not oversights)

- **No OCR.** Image-only pages are skipped, not read. Scanned PDFs are a V2 item.
- **No table structure.** Tables extract as flowed text. Fine for handbooks and
  SOPs; a dense numeric rate table would need dedicated handling.
- **Token counts are approximated** at 4 chars/token. Exact tokenisation isn't
  worth a dependency here — the cap only has to keep chunks inside the model's
  window.
- **`.md`/`.txt` get synthesised page numbers.** They have no real pages, and the
  citation contract requires a number.
- **Overlap doesn't cross section boundaries.** An answer split across a section
  boundary relies on top-k pulling both chunks.

## What V1 needs from this

- `VectorStore.query()` returns `Retrieved` objects with `.citation`, `.text` and
  `.score` — that's what feeds the answer prompt and the citation drawer.
- `VectorStore.sources()` backs the sidebar document picker.
- `config.REFUSAL_STRING` is the single refusal string; the grounding prompt and
  any test asserting refusal should both read it from there.
- Gate the refusal on the similarity floor `verify_v0.py` suggests, *before*
  calling the model. A score gate can't be talked out of refusing; a prompt can.
