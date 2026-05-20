"""OAuth2 client_credentials token fetcher for the corp LLM gateway.

The gateway authenticates each LLM call with a short-lived bearer token
in the Authorization header (LiteLLM reads it from ``OPENAI_API_KEY``).
This module exchanges ``(client_id, client_secret, scope)`` for an
access token, caches it in memory, and refreshes shortly before expiry.

Configure in .env:
    OAUTH_TOKEN_URL, OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET, OAUTH_SCOPE

When ``OAUTH_TOKEN_URL`` is unset, the static ``OPENAI_API_KEY`` is used
as-is (handy for local testing with a hand-pasted token).
"""

from __future__ import annotations

import os
import threading
import time

import httpx

# Refresh a minute before the server-reported expiry so an in-flight LLM
# call can't sneak in just as the token flips invalid.
_REFRESH_SKEW_SECONDS = 60

_lock = threading.Lock()
_cached_token: str | None = None
_expires_at: float = 0.0


def _fetch_token() -> tuple[str, float]:
    data = {
        "grant_type": "client_credentials",
        "client_id": os.environ["OAUTH_CLIENT_ID"],
        "client_secret": os.environ["OAUTH_CLIENT_SECRET"],
        "scope": os.environ["OAUTH_SCOPE"],
    }
    resp = httpx.post(os.environ["OAUTH_TOKEN_URL"], data=data, timeout=30.0, verify=False)
    resp.raise_for_status()
    body = resp.json()
    return body["access_token"], time.time() + int(body.get("expires_in", 3600))


def ensure_access_token() -> str | None:
    """Return a valid bearer token, refreshing if expired. Idempotent.

    Also mirrors the token into ``OPENAI_API_KEY`` so LiteLLM picks up
    the fresh value on its next call. Returns ``None`` (no-op) when
    ``OAUTH_TOKEN_URL`` is unset — in that mode the static
    ``OPENAI_API_KEY`` already in the env is used directly.
    """
    global _cached_token, _expires_at
    if not os.environ.get("OAUTH_TOKEN_URL"):
        return None
    with _lock:
        if _cached_token is None or time.time() + _REFRESH_SKEW_SECONDS >= _expires_at:
            _cached_token, _expires_at = _fetch_token()
            os.environ["OPENAI_API_KEY"] = _cached_token
        return _cached_token
