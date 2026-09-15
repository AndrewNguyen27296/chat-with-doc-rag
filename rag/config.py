"""Central configuration. Everything is env-overridable via .env."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# --- Retrieval / embedding ---
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# How all-MiniLM-L6-v2 is run. Same model either way; only the runtime differs.
#   "onnx"  — chromadb's bundled quantized ONNX build. Needs only onnxruntime,
#             which chromadb already installs. This is the deployable default:
#             sentence-transformers pulls torch, and on Linux PyPI's torch is
#             the CUDA build (a 554 MB wheel plus GBs of nvidia packages),
#             which does not fit Streamlit Community Cloud.
#   "sentence-transformers" — the original path. Install it yourself; it is
#             deliberately not in requirements.txt.
EMBEDDING_BACKEND = os.getenv("EMBEDDING_BACKEND", "onnx").strip().lower()
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", PROJECT_ROOT / ".chroma"))
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "company_docs")
TOP_K = int(os.getenv("TOP_K", "3"))

# --- Chunking ---
# The README specifies ~500-token chunks with 50-token overlap. We chunk on
# characters (fast, dependency-free) using a ~4 chars/token heuristic, which is
# accurate enough for English prose and keeps chunks comfortably inside the
# 256-token window of all-MiniLM-L6-v2 after the model's own truncation.
CHARS_PER_TOKEN = 4
CHUNK_TOKENS = int(os.getenv("CHUNK_TOKENS", "500"))
CHUNK_OVERLAP_TOKENS = int(os.getenv("CHUNK_OVERLAP_TOKENS", "50"))
CHUNK_SIZE = CHUNK_TOKENS * CHARS_PER_TOKEN
CHUNK_OVERLAP = CHUNK_OVERLAP_TOKENS * CHARS_PER_TOKEN

# --- Paths ---
SAMPLE_DOCS_DIR = PROJECT_ROOT / "sample_docs"

# --- Anti-hallucination guardrail (used by V1's generator) ---
REFUSAL_STRING = "I cannot find that information in the provided documentation."

# Pieces shorter than this are dropped: a bare heading stranded at a page foot
# is noise in a vector index, and its body is indexed with the next page.
MIN_CHUNK_CHARS = int(os.getenv("MIN_CHUNK_CHARS", "40"))

# --- V1: answer generation ---
# The model that writes the grounded answer. Kept as an env var rather than a
# pinned constant so the demo can move to a newer Sonnet without a code change.
ANSWER_MODEL = os.getenv("ANSWER_MODEL", "claude-sonnet-5")
# Output cap for one answer. On thinking models (Gemini 3.x, Claude with
# adaptive thinking) this cap INCLUDES the thinking tokens, and hitting it
# returns a truncated or empty answer rather than a shorter one. Keep it well
# above the two-or-three-sentence answer the prompt asks for: 1500 still
# truncated gemini-3.5-flash at its "low" thinking level on the live demo.
# The prompt, not this cap, is what keeps answers short.
MAX_ANSWER_TOKENS = int(os.getenv("MAX_ANSWER_TOKENS", "4096"))

# The pre-model refusal gate. If the best retrieved chunk scores below this,
# the app refuses *without* calling the model: cheaper than asking an LLM to
# decline, and a score cannot be argued out of its answer by a clever prompt.
#
# Measured, not guessed: `python scripts/verify_v0.py` on 2026-09-14 against the
# real all-MiniLM-L6-v2 ONNX model put the lowest in-scope top-1 score at 0.539
# and the highest off-topic score at 0.204, and suggested this floor. Re-run
# the script and update this if the corpus or the embedding model changes.
SIMILARITY_FLOOR = float(os.getenv("SIMILARITY_FLOOR", "0.37"))

# --- V1: model provider ---
# Which backend writes the answer: "auto" | "anthropic" | "gemini".
# "auto" picks whichever key is present, preferring the free tier.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto").strip().lower()

# Gemini via its OpenAI-compatible endpoint. One client class therefore also
# covers DeepSeek, Groq, OpenRouter and a local Ollama, should you add them.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
GEMINI_BASE_URL = os.getenv(
    "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"
)
# Gemini 3.x models think before they answer and cannot be told not to. At
# their default level ("medium") a short grounded answer spent most of the
# output cap thinking, and fragments of the reasoning leaked into the answer
# (seen on the live demo, 2026-09-15). "low" is plenty for reading three
# excerpts. Valid: "minimal" (not on every model), "low", "medium", "high";
# empty sends nothing, for endpoints that do not accept the parameter.
GEMINI_REASONING_EFFORT = os.getenv("GEMINI_REASONING_EFFORT", "low").strip().lower()

# --- Spend guard ---
# A public demo URL carries your key. Cap questions per browser session; past
# the cap the app degrades to retrieval-only instead of billing you. 0 = no cap.
MAX_QUESTIONS_PER_SESSION = int(os.getenv("MAX_QUESTIONS_PER_SESSION", "20"))
