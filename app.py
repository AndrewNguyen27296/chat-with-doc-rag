#!/usr/bin/env python3
"""Pillar 3 — Enterprise Operations SOP & Handbook Assistant.

    streamlit run app.py

The demo this serves: a specific policy question comes back in seconds with a
citation down to the page and section, an expandable drawer showing the exact
text the answer was drawn from, and a clean refusal for anything the documents
do not cover.

The refusal is gated on retrieval score before the model is called, so the
out-of-scope question in the demo costs nothing and cannot be talked out of
its answer.

Entrypoint for Streamlit Community Cloud. Everything it needs ships in the
repository — the two sample handbooks in sample_docs/ are indexed on first
boot, so a prospective client can test the whole flow without uploading a file.
"""

from __future__ import annotations

import os

import streamlit as st

from rag.chunker import chunk_pages
from rag.config import (
    LLM_PROVIDER,
    MAX_QUESTIONS_PER_SESSION,
    REFUSAL_STRING,
    SAMPLE_DOCS_DIR,
    SIMILARITY_FLOOR,
    TOP_K,
)
from rag.generator import Answer, best_score, should_refuse, stream_answer
from rag.golden import IN_SCOPE, OUT_OF_SCOPE
from rag.loader import load_directory
from rag.providers import resolve_provider

ALL_DOCUMENTS = "All documents"

st.set_page_config(
    page_title="SOP & Handbook Assistant",
    page_icon="📘",
    layout="centered",
    initial_sidebar_state="expanded",
)


STYLES = """
<style>
:root {
  --ink: #f8fafc;
  --muted: #94a3b8;
  --line: rgba(255, 255, 255, 0.12);
  --surface: rgba(255, 255, 255, 0.05);
  --accent: #38bdf8;
  --good: #34d399;
  --warn: #fbbf24;
}

/* Hero -------------------------------------------------------------- */
.hero { margin: 0 0 1.1rem 0; }
.hero h1 {
  font-size: clamp(1.45rem, 3.4vw, 2.05rem);
  line-height: 1.2;
  margin: 0 0 .35rem 0;
  letter-spacing: -0.015em;
  color: #f8fafc !important;
  font-weight: 700;
}
.hero p {
  margin: 0 0 .75rem 0;
  color: #94a3b8 !important;
  font-size: .95rem;
  max-width: 46rem;
}
.badges { display: flex; flex-wrap: wrap; gap: .4rem; }
.badge {
  display: inline-flex; align-items: center; gap: .35rem;
  border: 1px solid rgba(255, 255, 255, 0.15) !important;
  border-radius: 999px;
  padding: .2rem .6rem; font-size: .78rem;
  color: #cbd5e1 !important;
  background: rgba(255, 255, 255, 0.06) !important;
  white-space: nowrap;
}

/* Source cards ------------------------------------------------------ */
.src { border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 10px;
       padding: .7rem .85rem; margin-bottom: .6rem; background: rgba(255, 255, 255, 0.04); }
.src-head { display: flex; flex-wrap: wrap; align-items: baseline;
            gap: .5rem; margin-bottom: .45rem; }
.src-cite { font-weight: 600; font-size: .87rem; color: #38bdf8 !important; }
.src-score { font-size: .75rem; color: #94a3b8 !important;
             font-variant-numeric: tabular-nums; white-space: nowrap; }
.dot { display: inline-block; width: .5rem; height: .5rem;
       border-radius: 50%; margin-right: .3rem; vertical-align: baseline; }
.dot-good { background: #34d399; }
.dot-warn { background: #fbbf24; }
.src-text { font-size: .86rem; line-height: 1.55; color: #e2e8f0 !important;
            opacity: .95; }

/* How-it-works ------------------------------------------------------ */
.steps { display: grid; gap: .55rem;
         grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr)); }
.step { border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 10px;
        padding: .7rem .8rem; background: rgba(255, 255, 255, 0.04); }
.step b { display: block; font-size: .85rem; color: #f8fafc !important;
          margin-bottom: .15rem; }
.step span { font-size: .8rem; color: #94a3b8 !important; line-height: 1.45; }

/* Sidebar labels ---------------------------------------------------- */
.sb-label { font-size: .72rem; letter-spacing: .07em; text-transform: uppercase;
            color: #94a3b8 !important; margin: .2rem 0 .35rem 0; font-weight: 600; }
</style>
"""


# --- resources ---


@st.cache_resource(show_spinner=False)
def get_store():
    """One VectorStore for the session. Indexes the samples on a cold start."""
    from rag.vector_store import VectorStore

    store = VectorStore()
    if store.count() == 0:
        pages = load_directory(SAMPLE_DOCS_DIR)
        if pages:
            store.add_chunks(chunk_pages(pages))
    return store


def secret(name: str) -> str | None:
    """Read a key from Streamlit secrets (cloud) or the environment (local)."""
    try:
        value = st.secrets.get(name)  # type: ignore[union-attr]
        if value:
            return str(value)
    except Exception:
        pass
    return os.getenv(name) or None


@st.cache_resource(show_spinner=False)
def get_provider():
    """The answer backend, or None for retrieval-only mode."""
    return resolve_provider(
        secret("LLM_PROVIDER") or LLM_PROVIDER,
        gemini_key=secret("GEMINI_API_KEY"),
        anthropic_key=secret("ANTHROPIC_API_KEY"),
        gemini_model=secret("GEMINI_MODEL"),
    )


def questions_left() -> int | None:
    """Remaining questions this session, or None when uncapped."""
    if MAX_QUESTIONS_PER_SESSION <= 0:
        return None
    return max(0, MAX_QUESTIONS_PER_SESSION - st.session_state.get("asked", 0))


def render_counter(slot) -> None:
    """Draw the remaining-questions caption into a placeholder.

    The sidebar renders before the turn runs, so this is called again once the
    turn is done — otherwise the counter is always one question stale.
    """
    remaining = questions_left()
    if remaining is None:
        return
    with slot.container():
        st.caption(
            f"{remaining} of {MAX_QUESTIONS_PER_SESSION} model answers left "
            "this session"
        )
        if remaining == 0:
            st.caption("Cap reached — now answering in retrieval-only mode.")


# --- rendering ---


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


def source_card(hit, floor: float) -> str:
    """One retrieved chunk, rendered as a card.

    The dot is green when the chunk cleared the refusal floor. In a demo that
    makes the grounding rule visible rather than something to be asserted.
    """
    css = "dot-good" if hit.score >= floor else "dot-warn"
    excerpt = _escape(" ".join(hit.text.split()))
    return (
        f"<div class='src'>"
        f"<div class='src-head'>"
        f"<span class='src-cite'>{_escape(hit.citation)}</span>"
        f"<span class='src-score'><span class='dot {css}'></span>"
        f"similarity {hit.score:.3f}</span>"
        f"</div>"
        f"<div class='src-text'>{excerpt}</div>"
        f"</div>"
    )


def render_sources(citations, near_misses=None, floor: float = SIMILARITY_FLOOR) -> None:
    """The citation drawer. On a refusal, show what was rejected and why."""
    if citations:
        with st.expander(f"📚 View Cited Sources & Page Excerpts ({len(citations)})"):
            st.markdown(
                "".join(source_card(hit, floor) for hit in citations),
                unsafe_allow_html=True,
            )
        return

    if near_misses:
        with st.expander("🔍 Why this was refused"):
            st.caption(
                f"Nothing scored at or above the similarity floor of {floor:.2f}, "
                "so the question was refused without calling the model."
            )
            st.markdown(
                "".join(source_card(hit, floor) for hit in near_misses),
                unsafe_allow_html=True,
            )


def render_history() -> None:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                render_sources(
                    message.get("citations") or [],
                    message.get("near_misses") or [],
                    message.get("floor", SIMILARITY_FLOOR),
                )


def render_hero() -> None:
    st.markdown(
        "<div class='hero'>"
        "<h1>📘 Enterprise Operations SOP &amp; Handbook Assistant</h1>"
        "<p>Ask a question about your operating procedures, policies or staff "
        "handbooks. Every answer is grounded in the documents and cited to the "
        "exact page and section — and when the documents do not cover it, the "
        "assistant says so instead of guessing.</p>"
        "<div class='badges'>"
        "<span class='badge'>📄 Cited to page &amp; section</span>"
        "<span class='badge'>🛑 Refuses when unsupported</span>"
        "<span class='badge'>🔒 Embeddings run locally</span>"
        "<span class='badge'>⚡ Answers in seconds</span>"
        "</div></div>",
        unsafe_allow_html=True,
    )


def render_empty_state() -> None:
    st.markdown(
        "<div class='steps'>"
        "<div class='step'><b>1 · Pick a question</b><span>Use a sample question "
        "in the sidebar, or type your own below.</span></div>"
        "<div class='step'><b>2 · Read the citation</b><span>Every claim names "
        "its document, page and section.</span></div>"
        "<div class='step'><b>3 · Try the 🚫 one</b><span>An out-of-scope "
        "question is refused, not answered.</span></div>"
        "</div>",
        unsafe_allow_html=True,
    )


# --- the turn ---


def answer_question(question: str, scope: str | None, floor: float) -> None:
    store = get_store()

    with st.chat_message("user"):
        st.markdown(question)
    st.session_state.messages.append({"role": "user", "content": question})

    with st.chat_message("assistant"):
        with st.spinner("Searching the documentation…"):
            hits = store.query(question, top_k=TOP_K, source=scope)

        reason = should_refuse(hits, floor)

        if reason:
            st.markdown(REFUSAL_STRING)
            render_sources([], hits, floor)
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": REFUSAL_STRING,
                    "citations": [],
                    "near_misses": list(hits),
                    "floor": floor,
                }
            )
            return

        provider = get_provider()
        remaining = questions_left()
        capped = remaining is not None and remaining <= 0

        if provider is None or capped:
            why = (
                "the per-session question limit has been reached"
                if capped
                else "no model API key is configured"
            )
            body = (
                f"**Retrieval-only mode** — {why}, so the grounded answer was not "
                "generated. Retrieval still ran: the sources below are exactly "
                "what the model would have been given.\n\n"
                f"Best match: `{best_score(hits):.3f}` similarity, above the "
                f"`{floor:.2f}` floor."
            )
            st.markdown(body)
            render_sources(hits, [], floor)
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": body,
                    "citations": list(hits),
                    "floor": floor,
                }
            )
            return

        st.session_state.asked = st.session_state.get("asked", 0) + 1
        try:
            text = st.write_stream(
                stream_answer(question, hits, provider=provider, floor=floor)
            )
            result = Answer(text=str(text), citations=list(hits))
            if not result.is_grounded:
                st.warning(
                    "This answer carries no inline citation. Per the project's "
                    "invariant that is a bug, not a style preference.",
                    icon="⚠️",
                )
            render_sources(hits, [], floor)
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": result.text,
                    "citations": list(hits),
                    "floor": floor,
                }
            )
        except Exception as exc:
            # Revert the asked counter so a server fault does not penalise the user
            st.session_state.asked = max(0, st.session_state.get("asked", 1) - 1)
            err_msg = str(exc)
            fallback_body = (
                "⚠️ **Upstream AI provider error** — the language model "
                f"service encountered an error (`{type(exc).__name__}`: `{err_msg}`).\n\n"
                "Document retrieval ran successfully and is unaffected. "
                "The relevant handbook passages are cited below."
            )
            st.markdown(fallback_body)
            render_sources(hits, [], floor)
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": fallback_body,
                    "citations": list(hits),
                    "floor": floor,
                }
            )


# --- page ---


def main() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "pending" not in st.session_state:
        st.session_state.pending = None
    if "asked" not in st.session_state:
        st.session_state.asked = 0

    st.markdown(STYLES, unsafe_allow_html=True)
    render_hero()

    with st.sidebar:
        st.markdown("<div class='sb-label'>Documents</div>", unsafe_allow_html=True)
        with st.spinner("Preparing the index…"):
            store = get_store()
        sources = store.sources()
        scope_label = st.selectbox(
            "Search scope",
            [ALL_DOCUMENTS, *sources],
            help="Restrict retrieval to a single document, or search everything.",
            label_visibility="collapsed",
        )
        scope = None if scope_label == ALL_DOCUMENTS else scope_label
        st.caption(f"{store.count()} chunks indexed · {len(sources)} documents")

        st.divider()
        st.markdown(
            "<div class='sb-label'>Try a question</div>", unsafe_allow_html=True
        )
        for question in IN_SCOPE:
            if st.button(question.question, use_container_width=True):
                st.session_state.pending = question.question
        st.caption("And one the documents cannot answer:")
        for question in OUT_OF_SCOPE:
            if st.button(f"🚫 {question.question}", use_container_width=True):
                st.session_state.pending = question.question

        st.divider()
        st.markdown("<div class='sb-label'>Grounding</div>", unsafe_allow_html=True)
        floor = st.slider(
            "Similarity floor",
            min_value=0.0,
            max_value=0.9,
            value=float(SIMILARITY_FLOOR),
            step=0.01,
            help=(
                "Below this score the app refuses before calling the model. "
                "Set the default from scripts/verify_v0.py."
            ),
        )
        provider = get_provider()
        if provider is None:
            st.caption(
                "⚠️ No model key found — retrieval-only mode. Set "
                "`GEMINI_API_KEY` or `ANTHROPIC_API_KEY`."
            )
        else:
            st.caption(f"`{provider.info.name}` · model `{provider.info.model}`")
            if provider.info.free_tier:
                st.caption(f"🆓 {provider.info.caveat}")

        counter_slot = st.empty()
        render_counter(counter_slot)
        if st.button("Clear conversation", use_container_width=True):
            st.session_state.messages = []
            st.session_state.pending = None
            st.rerun()  # note: does not reset `asked` — the cap is per session

    if not st.session_state.messages:
        render_empty_state()

    render_history()

    typed = st.chat_input("Ask about a policy, SOP or handbook…")
    question = typed or st.session_state.pending
    if question:
        st.session_state.pending = None
        answer_question(question, scope, floor)
        render_counter(counter_slot)


if __name__ == "__main__":
    main()
