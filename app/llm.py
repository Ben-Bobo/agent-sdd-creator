"""Thin LiteLLM wrapper. Three functions: complete, complete_json, stream.

Model strings include a provider prefix (e.g. ``anthropic/...``,
``openai/...``). Code references semantic roles (``MODEL_MAIN`` /
``MODEL_CHEAP``) via env, never hardcoded model strings.

The system prompt is marked as cacheable on every call. On Anthropic this
gives a ~90% discount on the cached prefix (5-min TTL). LiteLLM strips
the marker for providers that don't support it; OpenAI's automatic prefix
caching kicks in regardless.
"""

from __future__ import annotations

import os
import sys
from collections.abc import AsyncIterator
from typing import TypeVar

import litellm
from pydantic import BaseModel, ValidationError

from .auth import ensure_access_token

T = TypeVar("T", bound=BaseModel)

litellm.suppress_debug_info = True


def _cached_system(text: str) -> list[dict]:
    """System message content with an Anthropic cache breakpoint at the end.

    Anthropic caches the prefix up to and including this block (5-min TTL).
    Per-call ``messages`` after it stay un-cached and get reprocessed each
    time, which is what we want — the system prompt + schema is static,
    the user turn is not.
    """
    return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]


def _token_limit_kwarg(model: str, value: int) -> dict:
    """Pick ``max_tokens`` vs ``max_completion_tokens`` based on the model.

    Newer OpenAI / Azure deployments (gpt-4o on current API versions, the
    o-series reasoning models) only accept ``max_completion_tokens``.
    Anthropic and older OpenAI models still use ``max_tokens``.

    Special case: corporate gateways often expose Claude models behind an
    ``openai/`` prefix but route them to Bedrock under the hood. Those
    Bedrock-routed Claude deployments accept ``max_tokens`` but NOT
    ``max_completion_tokens`` (the gateway translates the latter into the
    legacy ``max_tokens_to_sample`` which current Bedrock Claude rejects).
    So when the model name says "claude", always send ``max_tokens``.
    """
    lower = model.lower()
    if "claude" in lower or "anthropic" in lower:
        return {"max_tokens": value}
    if model.startswith(("openai/", "azure/", "azure_ai/")):
        return {"max_completion_tokens": value}
    return {"max_tokens": value}


def _log_usage(resp) -> None:
    """Print cached-vs-uncached input tokens to stderr when LLM_LOG_USAGE=1.

    Useful for confirming a caching change is actually firing. Off by default
    to keep normal runs quiet.
    """
    if os.environ.get("LLM_LOG_USAGE") != "1":
        return
    usage = getattr(resp, "usage", None)
    if usage is None:
        return
    details = getattr(usage, "prompt_tokens_details", None)
    cached = getattr(details, "cached_tokens", 0) if details else 0
    total_in = getattr(usage, "prompt_tokens", 0)
    total_out = getattr(usage, "completion_tokens", 0)
    sys.stderr.write(f"[llm] in={total_in} (cached={cached}) out={total_out}\n")


def complete(system: str, messages: list[dict], model: str, max_tokens: int = 4096) -> str:
    ensure_access_token()
    resp = litellm.completion(
        model=model,
        messages=[{"role": "system", "content": _cached_system(system)}] + messages,
        temperature=0,
        **_token_limit_kwarg(model, max_tokens),
    )
    _log_usage(resp)
    return resp.choices[0].message.content


def complete_json(
    system: str,
    messages: list[dict],
    schema: type[T],
    model: str,
    max_tokens: int = 4096,
    max_retries: int = 2,
) -> T:
    """Ask the model for strict JSON and parse it against `schema`.

    Uses the provider's native structured-output mode via LiteLLM:
    OpenAI → ``response_format`` with json_schema (strict), Anthropic →
    forced tool-call. Schema conformance is enforced by the API where
    supported, so the retry loop below is belt-and-suspenders for
    fallback providers and the occasional partial-validation edge case
    that Pydantic catches but the API didn't.
    """
    conv = list(messages)
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        ensure_access_token()
        resp = litellm.completion(
            model=model,
            messages=[{"role": "system", "content": _cached_system(system)}] + conv,
            response_format=schema,
            temperature=0,
            **_token_limit_kwarg(model, max_tokens),
        )
        _log_usage(resp)
        raw = resp.choices[0].message.content
        # Defensive: native mode returns raw JSON, but fallback providers
        # occasionally wrap in markdown fences.
        cleaned = (
            raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        )
        try:
            return schema.model_validate_json(cleaned)
        except (ValidationError, ValueError) as e:
            last_error = e
            sys.stderr.write(f"[complete_json] attempt {attempt + 1} failed validation; retrying\n")
            conv.append({"role": "assistant", "content": raw})
            conv.append(
                {
                    "role": "user",
                    "content": f"Your output failed validation: {e}. "
                    f"Return ONLY valid JSON matching the schema. No prose.",
                }
            )
    raise RuntimeError(f"complete_json failed after {max_retries + 1} attempts: {last_error}")


async def stream(
    system: str, messages: list[dict], model: str, max_tokens: int = 4096
) -> AsyncIterator[str]:
    ensure_access_token()
    resp = await litellm.acompletion(
        model=model,
        messages=[{"role": "system", "content": _cached_system(system)}] + messages,
        stream=True,
        temperature=0,
        **_token_limit_kwarg(model, max_tokens),
    )
    async for chunk in resp:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
