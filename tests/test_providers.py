#!/usr/bin/env python3
"""Provider tests: both SDK call shapes, and the auto-resolution rules.

    python tests/test_providers.py     # or: pytest -q

Fake SDK clients throughout — no keys, no network. What these pin is the shape
of the call each vendor expects, which is exactly what silently breaks when a
backend is swapped.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rag.providers import (  # noqa: E402
    AnthropicProvider,
    OpenAICompatProvider,
    anthropic_provider,
    gemini_provider,
    resolve_provider,
)


# --- fake anthropic SDK ---


class _AnthropicStream:
    def __init__(self, chunks):
        self._chunks = chunks

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    @property
    def text_stream(self):
        return iter(self._chunks)


class FakeAnthropic:
    def __init__(self, chunks=("Two hours ", "[Doc.pdf, Page 4]")):
        self.calls: list[dict] = []
        outer = self

        class Messages:
            def stream(self, **kwargs):
                outer.calls.append(kwargs)
                return _AnthropicStream(list(chunks))

        self.messages = Messages()


# --- fake OpenAI-compatible SDK ---


class _Delta:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.delta = _Delta(content)


class _Chunk:
    def __init__(self, content):
        self.choices = [_Choice(content)]


class FakeOpenAI:
    """Mimics client.chat.completions.create(stream=True)."""

    def __init__(
        self,
        chunks=("Two hours ", "[Doc.pdf, Page 4]"),
        reject_max_tokens=False,
        reject_reasoning=False,
    ):
        self.calls: list[dict] = []
        outer = self

        class BadRequest(Exception):
            """Shaped like openai.BadRequestError: a 400 from the endpoint."""

            status_code = 400

        class Completions:
            def create(self, **kwargs):
                if reject_max_tokens and "max_tokens" in kwargs:
                    raise TypeError("unexpected keyword argument 'max_tokens'")
                if reject_reasoning and "reasoning_effort" in kwargs:
                    raise BadRequest("Unknown parameter: reasoning_effort")
                outer.calls.append(kwargs)
                return iter([_Chunk(c) for c in chunks])

        class Chat:
            completions = Completions()

        self.chat = Chat()


# --- anthropic shape ---


def test_anthropic_passes_system_as_a_top_level_field():
    fake = FakeAnthropic()
    provider = AnthropicProvider(model="claude-x", client=fake)
    out = "".join(provider.stream(system="SYS", user="USER", max_tokens=42))
    assert out == "Two hours [Doc.pdf, Page 4]"
    call = fake.calls[0]
    assert call["system"] == "SYS"
    assert call["model"] == "claude-x"
    assert call["max_tokens"] == 42
    assert call["messages"] == [{"role": "user", "content": "USER"}]


# --- openai-compatible shape ---


def test_openai_compat_passes_system_as_a_message():
    fake = FakeOpenAI()
    provider = OpenAICompatProvider(
        api_key="k", base_url="http://x/", model="m", client=fake
    )
    out = "".join(provider.stream(system="SYS", user="USER", max_tokens=42))
    assert out == "Two hours [Doc.pdf, Page 4]"
    call = fake.calls[0]
    assert call["messages"][0] == {"role": "system", "content": "SYS"}
    assert call["messages"][1] == {"role": "user", "content": "USER"}
    assert call["stream"] is True
    assert call["max_tokens"] == 42


def test_openai_compat_retries_without_max_tokens_when_rejected():
    """A compat layer that renamed max_tokens must not kill the demo."""
    fake = FakeOpenAI(reject_max_tokens=True)
    provider = OpenAICompatProvider(
        api_key="k", base_url="http://x/", model="m", client=fake
    )
    out = "".join(provider.stream(system="SYS", user="USER", max_tokens=42))
    assert out == "Two hours [Doc.pdf, Page 4]"
    assert "max_tokens" not in fake.calls[0]


def test_openai_compat_skips_empty_deltas():
    fake = FakeOpenAI(chunks=("A", None, "", "B"))
    provider = OpenAICompatProvider(
        api_key="k", base_url="http://x/", model="m", client=fake
    )
    assert "".join(provider.stream(system="s", user="u", max_tokens=1)) == "AB"


# --- gemini wiring ---


def test_gemini_targets_the_openai_compatible_endpoint():
    provider = gemini_provider(api_key="k", client=FakeOpenAI())
    assert provider.base_url.endswith("/v1beta/openai/")
    assert provider.info.name == "gemini"


def test_gemini_is_flagged_free_tier_with_a_caveat():
    provider = gemini_provider(api_key="k", client=FakeOpenAI())
    assert provider.info.free_tier is True
    assert provider.info.caveat, "the free-tier data caveat must reach the UI"


def test_anthropic_is_not_flagged_free_tier():
    assert anthropic_provider(api_key="k", client=FakeAnthropic()).info.free_tier is False


# --- resolution ---


def test_no_keys_resolves_to_none_for_retrieval_only_mode():
    assert resolve_provider("auto", gemini_key=None, anthropic_key=None) is None


def test_auto_prefers_the_free_tier_when_both_keys_are_present():
    provider = resolve_provider("auto", gemini_key="g", anthropic_key="a")
    assert provider is not None and provider.info.name == "gemini"


def test_auto_falls_back_to_anthropic_when_only_that_key_is_present():
    provider = resolve_provider("auto", gemini_key=None, anthropic_key="a")
    assert provider is not None and provider.info.name == "anthropic"


def test_explicit_choice_is_honoured_over_the_other_key():
    provider = resolve_provider("anthropic", gemini_key="g", anthropic_key="a")
    assert provider is not None and provider.info.name == "anthropic"


def test_explicit_choice_without_its_key_is_none_not_a_silent_swap():
    """Asking for anthropic and silently getting gemini would send a client's
    documents to a free tier without anyone deciding to."""
    assert resolve_provider("anthropic", gemini_key="g", anthropic_key=None) is None


def _run() -> int:
    tests = [(n, o) for n, o in sorted(globals().items()) if n.startswith("test_")]
    failures = 0
    for name, func in tests:
        try:
            func()
            print(f"pass  {name}")
        except AssertionError as error:
            failures += 1
            print(f"FAIL  {name}: {error}")
        except Exception as error:  # noqa: BLE001
            failures += 1
            print(f"ERROR {name}: {type(error).__name__}: {error}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    return 1 if failures else 0


# --- thinking level (Gemini 3.x thinks against max_tokens) ---


def test_gemini_sends_a_low_reasoning_effort_by_default():
    """Seen live 2026-09-15: at the default thinking level a 600-token cap came
    back as reasoning fragments with the answer cut off."""
    from rag.providers import gemini_provider

    fake = FakeOpenAI()
    provider = gemini_provider(api_key="k", client=fake)
    out = "".join(provider.stream(system="SYS", user="USER", max_tokens=1500))
    assert out == "Two hours [Doc.pdf, Page 4]"
    assert fake.calls[0]["reasoning_effort"] == "low"
    assert fake.calls[0]["max_tokens"] == 1500


def test_generic_compat_provider_sends_no_reasoning_effort():
    """Groq, Ollama and friends may not accept it; only send it when asked."""
    from rag.providers import OpenAICompatProvider

    fake = FakeOpenAI()
    provider = OpenAICompatProvider(api_key="k", base_url="http://x", model="m", client=fake)
    "".join(provider.stream(system="SYS", user="USER", max_tokens=42))
    assert "reasoning_effort" not in fake.calls[0]


def test_openai_compat_retries_without_reasoning_effort_when_rejected():
    """A 400 for the thinking parameter must not kill the demo either."""
    from rag.providers import OpenAICompatProvider

    fake = FakeOpenAI(reject_reasoning=True)
    provider = OpenAICompatProvider(
        api_key="k", base_url="http://x", model="m", client=fake, reasoning_effort="low"
    )
    out = "".join(provider.stream(system="SYS", user="USER", max_tokens=42))
    assert out == "Two hours [Doc.pdf, Page 4]"
    assert "reasoning_effort" not in fake.calls[0]
    assert fake.calls[0]["max_tokens"] == 42


if __name__ == "__main__":
    raise SystemExit(_run())
