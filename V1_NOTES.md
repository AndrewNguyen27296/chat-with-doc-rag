# V1 — The Conversational Hero Demo

Built 2026-09-09. V0 proved the right pages come back; V1 turns that into the
answer, the citation drawer, and the refusal.

## Run it

```bash
python -m venv .venv && .venv\Scripts\activate     # Windows
pip install -r requirements.txt

python scripts/verify_v0.py         # closes the last V0 box — do this first
copy .env.example .env              # then put your ANTHROPIC_API_KEY in it
streamlit run app.py
```

The app indexes `sample_docs/` on first load if the collection is empty, so
there is no separate setup step before the demo.

Tests need no key and no network:

```bash
python tests/test_pipeline.py       # 21 — ingestion, chunking, metadata
python tests/test_generator.py      # 16 — grounding prompt, refusal gate
```

## What's new in here

| Path | Does |
| :--- | :--- |
| `rag/generator.py` | The grounding layer. Strict system prompt built from `config.REFUSAL_STRING`, retrieved chunks rendered as numbered `<excerpt>` blocks with their citation, the score gate, and Claude streaming. No Streamlit, `anthropic` imported lazily — so it is testable with a fake client. |
| `app.py` | The Streamlit demo. Chat history in session state, `st.write_stream` for the answer, citation drawer under every turn, sidebar document scope picker and 1-click sample questions read from `rag/golden.py`. |
| `tests/test_generator.py` | 16 tests on the grounding contract. |
| `rag/providers.py` | Answer backends behind one narrow protocol, mirroring `Embedder`. `AnthropicProvider` and `OpenAICompatProvider` — the latter covers Gemini's compatibility endpoint today, and DeepSeek, Groq, OpenRouter or a local Ollama by changing `base_url` and `model`. |
| `tests/test_providers.py` | 12 tests on the two SDK call shapes and the resolution rules. |
| `config.SIMILARITY_FLOOR` | The pre-model refusal gate. Measured 2026-09-14: `verify_v0.py` suggested 0.37 from the real model, and that is now the default. |
| `config.MAX_QUESTIONS_PER_SESSION` | The spend guard. Model answers per browser session before the app degrades to retrieval-only. |
| `config.EMBEDDING_BACKEND` | `onnx` (default, deployable) or `sentence-transformers` (opt-in, pulls torch). Same model either way. |
| `.streamlit/config.toml` | Theme and server settings; Streamlit Cloud reads it. |
| `requirements-dev.txt` | reportlab + pytest, kept out of the deploy install. |

## Design decisions worth knowing

**The refusal is a number, not a request.** `should_refuse()` runs before the
model is called: no hits, or a top score below `SIMILARITY_FLOOR`, and the app
emits `REFUSAL_STRING` without touching the network. A prompt can be argued out
of declining; a threshold cannot. `test_refused_question_never_reaches_the_model`
asserts the client is never called, which is the part that would silently rot.

**The drawer shows what the model was actually given.** `Answer.citations` is
the same list that was rendered into the prompt, so the drawer cannot claim a
source the model never saw. On a refusal the drawer flips to *"Why this was
refused"* and shows the rejected near-misses with their scores — in a client
demo, being able to say *"nothing scored above 0.19, so it declined"* is worth
more than the refusal sentence alone.

**An uncited answer is surfaced as a bug.** `Answer.is_grounded` checks for an
inline bracket citation and the UI raises a visible warning when it is missing,
rather than letting a quiet regression pass as a clean answer.

**The prompt tells the model not to obey the documents.** Rule 7 exists because
the excerpts are attacker-controlled the moment a client uploads their own
files. A handbook containing "ignore previous instructions" is a prompt
injection, and the excerpts are explicitly framed as quoted material.

**No key still demos.** Without `ANTHROPIC_API_KEY` the app runs in
retrieval-only mode: it shows the citations it would have passed to the model.
Useful for testing the pipeline, and it means a missing secret on Streamlit
Cloud degrades instead of crashing.

**`ANSWER_MODEL` is an env var, not a constant.** Pinning a model ID in code
ages badly. The default is a `-latest` alias; bump it freely.

**Importing `rag.generator` does not pull in chromadb.** `Retrieved` is a
`TYPE_CHECKING`-only import, keeping V0's lightweight-import property intact.

## Cost, and why the provider is an env var

Measured from the verified run: 3 retrieved chunks at ~100 tokens each, a
~400-token system prompt and the question — roughly **750 input and 150 output
tokens per answer**. At Sonnet-class rates that is about **$0.0045 a question,
~220 questions per dollar**. A hundred prospects asking ten questions each
costs **under $5**.

So per-token price is not the lever worth pulling here. Two things are:

**The public URL carries your key.** Uncapped, a loop costs real money. Hence
`MAX_QUESTIONS_PER_SESSION`: past the cap the app answers in retrieval-only
mode, still showing citations. The score gate already helps — off-topic
questions are refused before the provider is called, so junk traffic is free.

**Free is a data decision, not a price decision.** Gemini's free tier costs
nothing and needs no card, and Google states free-tier content may be used to
improve their products. That is fine for the synthetic handbooks in
`sample_docs/` and disqualifying for a client's real HR documents. Same shape,
sharper, for any non-EU-hosted API: the buyer for this pillar is a VP of People
in the Nordics, the documents are employee handbooks, and procurement will ask
where the text goes. `ProviderInfo.free_tier` and `.caveat` exist so the UI
states this rather than hiding it. Not legal advice — but it is the objection
you will hear.

`resolve_provider("anthropic")` returns `None` rather than silently falling
back to Gemini when the Anthropic key is missing. A silent swap would route a
client's documents to a free tier without anyone deciding to;
`test_explicit_choice_without_its_key_is_none_not_a_silent_swap` pins that.

**Gemini model IDs**, confirmed from Google's model docs on 2026-09-09:
`gemini-3.5-flash` (the default here), `gemini-3.5-flash-lite` for higher
free-tier throughput, `gemini-3.8-flash` for the best answers. All have a free
tier.

## Verification status

Run on the device VM, 2026-09-09:

- `tests/test_pipeline.py` — **21/21**, now including
  `test_vector_store_roundtrip_preserves_metadata` against real ChromaDB
  **1.5.9**. The store code was written against `chromadb>=0.5` and needed no
  change on 1.x — that was an open risk.
- `tests/test_generator.py` — **16/16** (reworked onto the provider seam).
- `tests/test_providers.py` — **12/12**.
- `scripts/verify_v0.py` — ran end-to-end for the first time. 57 chunks indexed
  in 0.3 s; **all 7 in-scope golden questions returned at rank 1** with the
  expected page *and* section; retrieval latency mean 8 ms, max 9 ms.
- `ingest.py index --reset` / `query` / `stats` — all three work. The demo query
  returns `Global_Logistics_Operating_Handbook.pdf, Page 4, Section 4.2` at
  rank 1.
- `app.py` — driven through `streamlit.testing.v1.AppTest` on Streamlit 1.63:
  cold-start indexing, sample-question buttons, streamed answer, citation
  drawer with page + section, and the out-of-scope refusal path with no
  citations offered. Zero exceptions on every path.
- The Gemini path was driven the same way with a fake OpenAI client: the
  grounding prompt arrives as a system *message*, the model id is passed
  through, and the free-tier caveat renders in the sidebar. The spend guard was
  tripped deliberately — with the cap at 2, the third question did not reach
  the provider and the app degraded to retrieval-only with citations intact.

**Untested against the live Gemini API.** `generativelanguage.googleapis.com`
is not reachable from the build environment, so the call *shape* is pinned by
tests but the round trip is not. Checked against the real SDK (openai 3.10.0):
the client constructs against Gemini's base URL and
`chat.completions.create` accepts `model`, `messages`, `stream` and
`max_tokens`. What is still unverified is whether Google's compatibility layer
*honours* `max_tokens` server-side. `OpenAICompatProvider.stream` retries
without it on a `TypeError`, which covers an SDK signature change but not a
server-side rejection — that would surface as an API error on the first real
call. First run with a real key is the check.

### The one caveat, and it matters

**All of the above ran with a TF-IDF stand-in embedder, not all-MiniLM-L6-v2.**
`huggingface.co`, `chroma-onnx-models.s3.amazonaws.com` and
`download.pytorch.org` are all blocked by egress policy in the build
environment; only PyPI is reachable, so the model weights could not be
downloaded. Everything downstream of the vectors is proven; MiniLM's own
ranking is not.

So **the similarity numbers in this file and in the app's default are not real.**
TF-IDF scores near zero off-topic and its measured margin gave a suggested
floor of 0.19. Dense embeddings never score a true zero. Run
`python scripts/verify_v0.py` on a machine with normal internet and put *its*
suggested floor into `SIMILARITY_FLOOR`. Until then the 0.35 default is a
guess. *(Resolved 2026-09-14 — see "Known limits and open risks".)*

## Made deploy-ready (2026-09-11)

Against the repository-isolation and Streamlit Cloud standards:

**The embedder moved to ONNX, and that is the substantive change.**
`sentence-transformers` pulls `torch`; on Linux PyPI's `torch` is the CUDA
build — a 554 MB wheel plus several GB of nvidia packages — which does not fit
a Community Cloud app. `rag/vector_store.py` now defaults to chromadb's bundled
quantized ONNX build of *the same* model, `all-MiniLM-L6-v2`, on `onnxruntime`,
which chromadb already installs. `EMBEDDING_BACKEND=sentence-transformers`
restores the old path locally.

Chroma's ONNX implementation L2-normalises its output, exactly as the
sentence-transformers path did with `normalize_embeddings=True`, so
`1 - cosine_distance` is still an exact cosine similarity and nothing
downstream changes. The collection now records `embedding_backend` in its
metadata, so an index built by one runtime is identifiable.

`default_embedder()` falls back to ONNX on an unrecognised value rather than
raising — a typo in an env var on a deployed demo should not take the app down.

**Dependencies are pinned and lean.** `requirements.txt` is runtime-only, six
packages, exact pins verified together. `reportlab` (sample-doc generation) and
`pytest` moved to `requirements-dev.txt`. No `packages.txt` — there are no
system dependencies.

Pinned versions were checked against PyPI rather than recalled: `anthropic` is
**1.5.0**, not the 0.x the old range implied. Its `messages.stream(model,
max_tokens, system, messages)` shape is unchanged, so `AnthropicProvider`
needed no edit — but the range `anthropic>=0.28.0` would have silently pulled a
major version bump on a fresh deploy.

**Repository isolation** verified: no imports or path references reaching
outside this folder, and `app.py` is at the root. `.gitignore` now also
excludes `.streamlit/secrets.toml`.

**UI.** Hero header with trust badges, retrieved chunks as cards with a
green/amber dot showing whether each cleared the refusal floor, a three-step
empty state, and uppercase sidebar section labels. Styling is CSS-variable
based with a `prefers-color-scheme` override.

### The caveat on all of this

**The ONNX embedder has never been executed.** `chroma-onnx-models.s3.amazonaws.com`
is blocked by egress policy in every environment available here, so the weights
could not be downloaded even once. What is verified: the embedding function
constructs without network, chroma L2-normalises its output, and the wiring and
fallback logic are covered by tests using a stand-in embedder. What is not:
a single real embedding vector from it.

**First run on your machine is the check** — `python scripts/verify_v0.py`.
Expect it to download ~80 MB once. If the golden questions come back at rank 1,
the swap is good.

**And the similarity floor is still a placeholder.** It was never set from a
real run, and switching the embedding runtime changes the numbers again, so the
floor must come from a `verify_v0.py` run on the ONNX path. Until then `0.35`
is a guess — the one number in this project that is not measured.
*(Resolved 2026-09-14 — see "Known limits and open risks".)*

## Known limits and open risks

- **Resolved 2026-09-14:** the embedding-model gap and the placeholder floor.
  `scripts/verify_v0.py` ran on the ONNX path with the real `all-MiniLM-L6-v2`
  weights (79 MB, downloaded fresh). All 7 golden questions returned the
  expected page, 6 at rank 1 and one at rank 2. Lowest in-scope top-1 score
  0.539, highest off-topic 0.204, margin +0.336, retrieval ~180 ms. The
  suggested floor of 0.37 is now the `SIMILARITY_FLOOR` default.
- **Resolved 2026-09-11:** the torch/Streamlit Cloud risk. The default
  embedder is now chromadb's ONNX build and `torch` is gone from the dependency
  set — but see the caveat above: that path is wired and tested, not yet run.
- **Cold boot downloads ~80 MB.** The ONNX weights are fetched on first use and
  cached. On Streamlit Cloud that cost is paid on each cold start of a fresh
  container, not per request.
- **No conversational memory in retrieval.** Each question is embedded on its
  own, so "what about for contractors?" as a follow-up retrieves on those words
  alone. Query rewriting from history is a V2 item.
- **`st.cache_resource` holds one store per server**, so a Streamlit Cloud
  restart re-indexes on the first request. Fine for two sample PDFs, wrong for
  a client corpus — that wants a pre-built index shipped alongside.
- **No upload path yet.** Documents come from `sample_docs/`. Multi-document
  upload is a V2 item in the README.
- **The floor is global.** One threshold across both handbooks. A corpus mixing
  dense policy prose with sparse reference tables may want per-source floors.
