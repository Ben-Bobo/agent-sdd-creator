"""Thin LiteLLM wrapper. Three functions: complete, complete_json, stream.

Model strings include a provider prefix (e.g. ``anthropic/...``,
``openai/...``). Code references semantic roles (``MODEL_MAIN`` /
``MODEL_CHEAP``) via env, never hardcoded model strings.
"""
from __future__ import annotations

import json
import sys
from typing import AsyncIterator, Type, TypeVar

import litellm
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

litellm.suppress_debug_info = True


def complete(system: str, messages: list[dict], model: str,
             max_tokens: int = 4096) -> str:
    resp = litellm.completion(
        model=model,
        messages=[{"role": "system", "content": system}] + messages,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content


def complete_json(system: str, messages: list[dict],
                  schema: Type[T], model: str,
                  max_tokens: int = 4096, max_retries: int = 2) -> T:
    """Ask the model for strict JSON and parse it against `schema`.
    Retry on validation failure with a feedback turn."""
    schema_json = json.dumps(schema.model_json_schema(), indent=2)
    system_with_schema = (
        f"{system}\n\n"
        f"Respond with ONLY valid JSON matching this schema. "
        f"No markdown fences, no commentary.\n\n"
        f"Schema:\n{schema_json}"
    )
    conv = list(messages)
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        raw = complete(system_with_schema, conv, model, max_tokens)
        cleaned = (
            raw.strip()
            .removeprefix("```json")
            .removeprefix("```")
            .removesuffix("```")
            .strip()
        )
        try:
            return schema.model_validate_json(cleaned)
        except (ValidationError, ValueError) as e:
            last_error = e
            sys.stderr.write(
                f"[complete_json] attempt {attempt + 1} failed validation; retrying\n"
            )
            conv.append({"role": "assistant", "content": raw})
            conv.append({"role": "user", "content":
                f"Your output failed validation: {e}. "
                f"Return ONLY valid JSON matching the schema. No prose."})
    raise RuntimeError(
        f"complete_json failed after {max_retries + 1} attempts: {last_error}"
    )


async def stream(system: str, messages: list[dict], model: str,
                 max_tokens: int = 4096) -> AsyncIterator[str]:
    resp = await litellm.acompletion(
        model=model,
        messages=[{"role": "system", "content": system}] + messages,
        max_tokens=max_tokens,
        stream=True,
    )
    async for chunk in resp:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
