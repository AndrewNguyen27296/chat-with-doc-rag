# 💬 Pillar 3: Chat with Company Docs (Enterprise RAG Knowledge Agent)

> **The North Star:** *"The Hallucination-Free Enterprise Brain."*  
> An employee or customer support agent asks a complex, nuanced question about internal company policies, standard operating procedures (SOPs), or vendor contracts, and receives an instant, grounded answer in 3 seconds—with verifiable, clickable citations down to the exact page and paragraph.

**Status: V1 live.** Repository: https://github.com/AndrewNguyen27296/chat-with-doc-rag. Live demo: https://chat-with-doc-rag-lzzmbgqojbwksctngsbmeg.streamlit.app/ — deployed to Streamlit Community Cloud on 2026-09-15 and smoke-tested cold: the demo question answers with a page-and-section citation, the off-topic question is refused before the model is called, and the per-session spend guard shows in the sidebar. See `CLAUDE.md` for the portfolio-wide plan and the deploy recipe.

---

## 🧭 1. Vision & The Strategic "Why"

### The Target Persona (The Buyer):
* **Who:** VP of People/HR, Chief of Staff, Operations Director, or Customer Success Lead.
* **Their Daily Hell:** The company has a 90-page employee handbook, 40 process SOPs, and dozens of vendor guidelines buried in Google Drive. Junior staff interrupt managers on Slack 15 times a day asking basic questions (*"What is our refund window for international customers?"*, *"What are the dental insurance co-pay limits?"*).
* **The Transformed State:** A secure, private conversational AI assistant answers immediately in natural language. Every single sentence is backed by an explicit citation (*"[Handbook_2026.pdf, Page 34]"*). If a policy doesn't exist, the bot explicitly says so rather than guessing.

### The 60-Second "Wow Moment" (Your Demo North Star):
1. The prospective client opens your live Streamlit demo.
2. In the sidebar, they select a pre-loaded sample document (e.g. **"Global Logistics Operating Handbook & Policy Manual"**).
3. They type an obscure, specific question:
   > *"What happens if a freight carrier reports temperature abuse on perishable cargo over the weekend?"*
4. In under 3 seconds, the assistant streams a crisp, professional 2-sentence response:
   > *"In the event of weekend temperature deviation exceeding 4°C, the on-duty dispatcher must notify the cold-chain quality lead within 2 hours and initiate Form CC-12 before goods leave the terminal [Handbook_v2.pdf, Page 28, Section 4.2]."*
5. Below the answer, an interactive drawer expands: **"📚 View Verified Source Excerpts"**, displaying the exact highlighted text chunk from Page 28.
6. Then they ask an out-of-scope question: *"Who won the 2022 World Cup?"* $\rightarrow$ The bot responds cleanly: *"I cannot find that information in the provided documentation."*
7. Client reaction: *"This is safe, accurate, and ready to deploy to our team tomorrow."*

---

## 🏛 2. Architectural Invariants (The Non-Negotiables During Vibe Coding)

When vibe coding with AI, enforce these technical guardrails:

1. **Non-Compete Invariant:** Zero energy efficiency manuals, utility tariff guidelines, or building carbon protocols. Use **Corporate Operations SOPs, HR Handbooks, Logistics Guidelines, or Software API Documentation**.
2. **Zero-Hallucination Guardrail:** The system prompt must enforce strict grounding:
   > *"Answer ONLY using the provided context chunks. If the context does not contain the answer, state clearly: 'I cannot find that information in the provided documentation.' Never extrapolate or invent external facts."*
3. **Metadata Retention Invariant:** Every text chunk stored in the vector database must retain its source metadata: `{"source": "filename.pdf", "page": int, "chunk_id": int}`. An answer without a page citation is considered a bug.
4. **Local / Private Vector Storage:** Use local **ChromaDB** or **FAISS** with zero external vector database hosting fees.

---

## 🗺 3. Phased Roadmap: From Vibe Coding to Paid Client Delivery

```
[V0: Ingestion & Vector RAG] ──► [V1: Conversational Hero Demo] ──► [V2: Commercial Offering]
(1 Evening - 2 Hours)            (1 Evening - 3 Hours)             (What You Sell for $2,500+)
```

### Phase V0: The Vector Search Engine (Evening 1 — Fast MVP)
* [x] **PDF Loader & Metadata Extractor (`rag/loader.py`):** Use `pypdf` or `pymupdf` to parse PDFs page-by-page, attaching `page_number` to every text slice.
* [x] **Recursive Chunking (`rag/chunker.py`):** Chunk text into ~500-token chunks with 50-token overlap to maintain semantic continuity.
* [x] **Local ChromaDB Vector Indexing (`rag/vector_store.py`):** Index chunks using a lightweight embedding model (`all-MiniLM-L6-v2` or Google embeddings).
* [x] **Retrieval Test:** Verify that querying returns top-3 relevant chunks with correct page numbers. *(Verified 2026-09-14 against the real `all-MiniLM-L6-v2` ONNX model via `python scripts/verify_v0.py`: all 7 golden questions return the expected page, 6 of them at rank 1; off-topic questions score at most 0.204 against an in-scope floor of 0.539, a +0.336 margin; retrieval ~180 ms.)*

### Phase V1: The Conversational Hero Demo (Evening 2 — Visual Delight)
* [x] **Streamlit Chat Interface (`app.py`):** Use `st.chat_message("user")` and `st.chat_message("assistant")` with persistent session state.
* [x] **Streamed Response & Citation Drawer:** Stream Claude Sonnet 5 / Gemini response, appending an expandable `st.expander("📚 View Cited Sources & Page Excerpts")` below each answer.
* [x] **Pre-Loaded Sample SOPs:** Include 2 sample corporate handbooks in the sidebar for instant 1-click evaluation without file uploads.
* [x] **Pluggable Answer Provider (`rag/providers.py`):** Anthropic plus any OpenAI-compatible endpoint (Gemini's free tier today; DeepSeek, Groq or a local Ollama by changing two env vars). Makes the Tier 1 "model selection" audit demonstrable rather than theoretical.
* [x] **Spend Guard:** Per-session cap on model answers; past it the app degrades to retrieval-only instead of billing you. A public URL carries your key.
* [x] **Deploy to Streamlit Cloud:** Public live URL ready to embed in proposals. *(Live at https://chat-with-doc-rag-lzzmbgqojbwksctngsbmeg.streamlit.app/ since 2026-09-15. Torch-free dependency set, pinned versions, no system packages, `app.py` at the root, samples indexed on first boot. See §7 below.)*

### Phase V2: Commercial Enterprise Delivery (The Upsell Package)
* [ ] **Multi-Document Ingestion:** Allow users to upload full folders of PDFs, DOCX, and Markdown files.
* [ ] **Hybrid Search:** Combine keyword BM25 search + dense vector embeddings for ultra-precise technical term retrieval.
* [ ] **User Feedback Logging:** Thumbs up / thumbs down buttons logging answers to evaluate and refine chunking quality over time.

---

## 📂 4. Project Directory Blueprint

```text
Pillar 3 - Chat with Docs RAG/
├── README.md                 # This North Star document
├── requirements.txt          # Pinned runtime dependencies (torch-free)
├── requirements-dev.txt      # Dev-only: sample-doc generation, pytest
├── .streamlit/config.toml    # Theme + server settings for Streamlit Cloud
├── .env.example              # API keys template
├── sample_docs/              # 2 sample corporate policy PDFs for 1-click testing
├── V0_NOTES.md               # V0 build notes & design decisions
├── V1_NOTES.md               # V1 build notes, verification status, deploy risks
├── ingest.py                 # CLI: index / query / stats
├── rag/
│   ├── config.py             # Env-overridable settings incl. SIMILARITY_FLOOR
│   ├── loader.py             # Page-aware PDF text extraction
│   ├── chunker.py            # Recursive character chunking with overlap
│   ├── vector_store.py       # ChromaDB embedding & similarity search
│   ├── golden.py             # Golden question set (the acceptance contract)
│   ├── providers.py          # Anthropic + OpenAI-compatible answer backends
│   └── generator.py          # Strict anti-hallucination prompt & LLM streaming
├── scripts/
│   ├── make_sample_docs.py   # Regenerate the two sample handbooks
│   └── verify_v0.py          # Retrieval acceptance check
├── tests/
│   ├── test_pipeline.py      # 21 ingestion/chunking/metadata tests
│   ├── test_generator.py     # 16 grounding & refusal-gate tests
│   └── test_providers.py     # 12 provider-shape & resolution tests
└── app.py                    # Streamlit conversational UI with citation drawers
```

---

## 📦 5. Starter Dependencies (`requirements.txt`)

```text
streamlit>=1.35.0
chromadb>=0.5.0
sentence-transformers>=2.7.0
pypdf>=4.2.0
anthropic>=0.28.0
python-dotenv>=1.0.1
```

---

## 🎥 6. The 60-Second Client Pitch Script

> *"Hi! In this quick 60-second walkthrough, I'm demonstrating an enterprise AI Knowledge Assistant I built for internal company documentation.*
> 
> *Instead of employees reading through a 70-page operational manual or customer service guide, they can ask specific questions in plain English.*
> 
> *Notice two key features: First, the assistant is strictly grounded—it never hallucinates or invents policies outside the uploaded files. Second, as you see here, every single answer includes an expandable citations box showing the exact document name and page number where the answer was found.*
> 
> *I can deploy a secure, custom knowledge agent like this for your team's SOPs, handbooks, or technical guides within a week. Click the live demo link below to test it with a sample handbook!"*

---

## 🚀 7. Deploying to Streamlit Community Cloud

The repository is standalone: no imports from sibling pillars, no system
packages, no `packages.txt` needed.

1. Push this folder to its own GitHub repository.
2. On [share.streamlit.io](https://share.streamlit.io), create an app pointing
   at that repo, branch `main`, main file `app.py`.
3. In **Advanced settings → Secrets**, paste:

   ```toml
   GEMINI_API_KEY = "your-key"
   ```

   Get a free key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey).
   Without a key the app still runs, in retrieval-only mode.
4. Deploy. First boot downloads the ~80 MB embedding model once, indexes the
   two sample handbooks, and is ready.

**Why the dependency set is torch-free.** `sentence-transformers` pulls
`torch`, and on Linux PyPI's `torch` is the CUDA build — a 554 MB wheel plus
several GB of nvidia packages, which does not fit a Community Cloud app.
Embeddings therefore run on chromadb's bundled quantized ONNX build of the same
model (`all-MiniLM-L6-v2`) via `onnxruntime`, which chromadb already installs.
Set `EMBEDDING_BACKEND=sentence-transformers` to go back, locally.

**Spend guard.** A public URL carries your key. `MAX_QUESTIONS_PER_SESSION`
(default 20) caps model answers per browser session; past it the app degrades
to retrieval-only rather than billing you. Off-topic questions are refused
before the model is called, so junk traffic is free.

**Thinking models.** Gemini 3.x thinks before it answers, and its thinking
tokens count against `MAX_ANSWER_TOKENS`. At the model's default thinking level
with the original 600-token cap, the live demo returned truncated answers with
fragments of the reasoning in them and no citation. The app now sends
`reasoning_effort=low` (`GEMINI_REASONING_EFFORT`) and caps at 4096 tokens,
which is plenty for a three-sentence grounded answer.
