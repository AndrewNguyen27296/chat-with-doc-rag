"""Answer-generation backends.

Mirrors the `Embedder` protocol in `vector_store.py`: the grounding layer in
`generator.py` depends on this narrow interface, not on any vendor SDK, so
swapping backends touches one class.

Two implementations cover the useful ground:

  * `AnthropicProvider` — the quality reference, and what paid client work
    normally runs on.
  * `OpenAICompatProvider` — any OpenAI-compatible /chat/completions endpoint.
    That is Gemini's compatibility layer today, and the same class would serve
    DeepSeek, Groq, OpenRouter or a local Ollama by changing base_url and model.

Which one is right is a commercial question, not a technical one. A free tier
is free because the provider may use the content; that is fine for the
synthetic sample handbooks and wrong for a client's real HR documents. See
`free_tier` and `caveat` on ProviderInfo — the UI surfaces them.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Iterator, Protocol, runtime_checkable

from rag.config import (
    ANSWER_MODEL,
    GEMINI_BASE_URL,
    GEMINI_MODEL,
    GEMINI_REASONING_EFFORT,
    LLM_PROVIDER,
)


@dataclass(frozen=True)
class ProviderInfo:
    """What the UI needs to say about the backend in use."""

    name: str
    model: str
    free_tier: bool = False
    caveat: str = ""


@runtime_checkable
class Provider(Protocol):
    info: ProviderInfo

    def stream(self, system: str, user: str, max_tokens: int) -> Iterator[str]:
        ...  # pragma: no cover


class AnthropicProvider:
    """Claude via the anthropic SDK. `client` is injectable for tests."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = ANSWER_MODEL,
        client: Any | None = None,
    ) -> None:
        self.model = model
        self._client = client
        self._api_key = api_key
        self.info = ProviderInfo(name="anthropic", model=model, free_tier=False)

    @property
    def client(self) -> Any:
        if self._client is None:
            import anthropic

            self._client = (
                anthropic.Anthropic(api_key=self._api_key)
                if self._api_key
                else anthropic.Anthropic()
            )
        return self._client

    def stream(self, system: str, user: str, max_tokens: int) -> Iterator[str]:
        with self.client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        ) as stream:
            for delta in stream.text_stream:
                yield delta


class OpenAICompatProvider:
    """Any OpenAI-compatible chat-completions endpoint.

    The system prompt goes in as a system message rather than a top-level
    field, which is the one shape difference from the Anthropic SDK.
    """

    def __init__(
        self,
        api_key: str | None,
        base_url: str,
        model: str,
        name: str = "openai-compatible",
        free_tier: bool = False,
        caveat: str = "",
        client: Any | None = None,
        reasoning_effort: str | None = None,
    ) -> None:
        self.model = model
        self.base_url = base_url
        self._api_key = api_key
        self._client = client
        # Thinking level for reasoning models; None sends nothing.
        self.reasoning_effort = reasoning_effort or None
        self.info = ProviderInfo(
            name=name, model=model, free_tier=free_tier, caveat=caveat
        )

    @property
    def client(self) -> Any:
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(api_key=self._api_key, base_url=self.base_url)
        return self._client

    def _create(self, request: dict[str, Any]) -> Any:
        """One streaming request, degrading gracefully on shape mismatches."""
        try:
            return self.client.chat.completions.create(**request)
        except TypeError:
            # Some compatibility layers renamed max_tokens. Losing the cap is
            # better than losing the demo.
            request = {k: v for k, v in request.items() if k != "max_tokens"}
            return self.client.chat.completions.create(**request)
        except Exception as error:
            # An endpoint that rejects reasoning_effort with a 400 (a non-Gemini
            # compat layer, say) should still answer at its own default level.
            rejected = getattr(error, "status_code", None) == 400
            if rejected and "reasoning_effort" in request:
                request = {k: v for k, v in request.items() if k != "reasoning_effort"}
                return self.client.chat.completions.create(**request)
            raise

    def stream(self, system: str, user: str, max_tokens: int) -> Iterator[str]:
        request: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": True,
            "max_tokens": max_tokens,
        }
        if self.reasoning_effort:
            # Thinking tokens count against max_tokens on Gemini 3.x. At the
            # default level the model thinks the cap away and the answer
            # arrives truncated, with reasoning fragments in it.
            request["reasoning_effort"] = self.reasoning_effort

        for chunk in self._create(request):
            choices = getattr(chunk, "choices", None)
            if not choices:
                continue
            delta = getattr(choices[0], "delta", None)
            text = getattr(delta, "content", None) if delta else None
            if text:
                yield text


GEMINI_CAVEAT = (
    "Free tier: Google states free-tier content may be used to improve their "
    "products. Fine for the synthetic sample handbooks, not for a client's "
    "real documents."
)


def gemini_provider(
    api_key: str | None = None,
    model: str = GEMINI_MODEL,
    client: Any | None = None,
    reasoning_effort: str | None = GEMINI_REASONING_EFFORT,
) -> OpenAICompatProvider:
    return OpenAICompatProvider(
        api_key=api_key or os.getenv("GEMINI_API_KEY"),
        base_url=GEMINI_BASE_URL,
        model=model,
        name="gemini",
        free_tier=True,
        caveat=GEMINI_CAVEAT,
        client=client,
        reasoning_effort=reasoning_effort,
    )


def anthropic_provider(
    api_key: str | None = None,
    model: str = ANSWER_MODEL,
    client: Any | None = None,
) -> AnthropicProvider:
    return AnthropicProvider(
        api_key=api_key or os.getenv("ANTHROPIC_API_KEY"), model=model, client=client
    )


def resolve_provider(
    choice: str = LLM_PROVIDER,
    gemini_key: str | None = None,
    anthropic_key: str | None = None,
) -> Provider | None:
    """Return a provider, or None when no key is configured.

    None is not an error: the app falls back to retrieval-only mode, which
    still demonstrates the citation drawer. A missing secret should degrade,
    not crash.
    """
    gemini_key = gemini_key or os.getenv("GEMINI_API_KEY") or None
    anthropic_key = anthropic_key or os.getenv("ANTHROPIC_API_KEY") or None

    if choice == "gemini":
        return gemini_provider(gemini_key) if gemini_key else None
    if choice == "anthropic":
        return anthropic_provider(anthropic_key) if anthropic_key else None

    # auto: prefer the free tier, so the public demo costs nothing by default.
    if gemini_key:
        return gemini_provider(gemini_key)
    if anthropic_key:
        return anthropic_provider(anthropic_key)
    return None
