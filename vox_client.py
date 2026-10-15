"""Pfizer Vox GenAI V2 client (OAuth + OpenAI-compatible chat)."""

from __future__ import annotations

import asyncio
from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import logging
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Iterator

import requests
from openai import OpenAI

from neo4j_client import load_env

logger = logging.getLogger(__name__)
_token_cache: dict[str, Any] = {"access_token": None, "expires_at": 0.0}
_llm_context: ContextVar[tuple[str, str | None]] = ContextVar(
    "llm_context", default=("vox", None)
)


def empty_usage() -> dict[str, int]:
    return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


def _usage_from_response(resp: Any) -> dict[str, int]:
    usage = empty_usage()
    raw = getattr(resp, "usage", None)
    if raw is None:
        return usage
    usage["prompt_tokens"] = int(getattr(raw, "prompt_tokens", 0) or 0)
    usage["completion_tokens"] = int(getattr(raw, "completion_tokens", 0) or 0)
    usage["total_tokens"] = int(
        getattr(raw, "total_tokens", 0)
        or (usage["prompt_tokens"] + usage["completion_tokens"])
    )
    return usage


def add_usage(a: dict[str, int], b: dict[str, int]) -> dict[str, int]:
    return {
        "prompt_tokens": a.get("prompt_tokens", 0) + b.get("prompt_tokens", 0),
        "completion_tokens": a.get("completion_tokens", 0) + b.get("completion_tokens", 0),
        "total_tokens": a.get("total_tokens", 0) + b.get("total_tokens", 0),
    }


def _vox_configured() -> bool:
    load_env()
    return bool(
        os.environ.get("VOX_GENAI_API")
        and os.environ.get("VOX_TOKEN_GEN_URL")
        and os.environ.get("VOX_CLIENT_ID")
        and os.environ.get("VOX_CLIENT_SECRET")
    )


def get_vox_access_token(force_refresh: bool = False) -> str:
    load_env()
    now = time.time()
    if (
        not force_refresh
        and _token_cache["access_token"]
        and now < float(_token_cache["expires_at"]) - 60
    ):
        return str(_token_cache["access_token"])

    resp = requests.post(
        os.environ["VOX_TOKEN_GEN_URL"],
        data={
            "grant_type": "client_credentials",
            "client_id": os.environ["VOX_CLIENT_ID"],
            "client_secret": os.environ["VOX_CLIENT_SECRET"],
        },
        timeout=60,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Vox token request failed ({resp.status_code}): {resp.text[:400]}")

    payload = resp.json()
    access_token = payload.get("access_token")
    if not access_token:
        raise RuntimeError(f"Vox token response missing access_token: {payload}")

    expires_in = int(payload.get("expires_in", 1800))
    _token_cache["access_token"] = access_token
    _token_cache["expires_at"] = now + expires_in
    return access_token


def build_llm_client() -> tuple[OpenAI, str]:
    load_env()

    if _vox_configured():
        token = get_vox_access_token()
        base = os.environ["VOX_GENAI_API"].rstrip("/")
        client = OpenAI(api_key=token, base_url=f"{base}/v1")
        model = os.environ.get("VOX_MODEL") or "gpt-4o"
        return client, model

    raise ValueError(
        "Missing Vox GenAI config. Set VOX_GENAI_API, VOX_TOKEN_GEN_URL, "
        "VOX_CLIENT_ID, and VOX_CLIENT_SECRET in Connect Vars or .env."
    )


def models_vox_genai() -> list[str]:
    client, _ = build_llm_client()
    response = client.models.list()
    data = getattr(response, "data", None)
    if data is None:
        raise RuntimeError("Vox models.list() response missing data")

    model_ids: list[str] = []
    for item in data:
        model_id = getattr(item, "id", None)
        if isinstance(model_id, str) and model_id.strip():
            model_ids.append(model_id.strip())

    # Keep order stable while de-duplicating.
    return list(dict.fromkeys(model_ids))


@contextmanager
def use_llm_provider(provider: str, github_token: str | None = None) -> Iterator[None]:
    if provider not in {"vox", "github_copilot"}:
        raise ValueError(f"Unsupported LLM provider: {provider}")
    if provider == "github_copilot" and not github_token:
        raise ValueError("GitHub Copilot requires a GitHub token.")
    context_token = _llm_context.set((provider, github_token))
    try:
        yield
    finally:
        _llm_context.reset(context_token)


def _copilot_base_directory(github_token: str) -> str:
    """Create isolated SDK storage without exposing the token in the directory name."""
    root = Path(os.environ.get("COPILOT_STORAGE_DIR", tempfile.gettempdir())) / "did-insight-copilot"
    tenant_id = hashlib.sha256(github_token.encode("utf-8")).hexdigest()
    directory = root / tenant_id
    directory.mkdir(parents=True, exist_ok=True)
    return str(directory)


async def _chat_with_github_copilot(system: str, user: str, github_token: str) -> str:
    from copilot import CopilotClient

    load_env()
    model = os.environ.get("COPILOT_MODEL") or "auto"
    async with CopilotClient(
        mode="empty",
        base_directory=_copilot_base_directory(github_token),
        use_logged_in_user=False,
        session_idle_timeout_seconds=300,
    ) as client:
        async with await client.create_session(
            model=model,
            github_token=github_token,
            available_tools=[],
            system_message={"mode": "replace", "content": system},
        ) as session:
            response = await session.send_and_wait(user)
    content = getattr(getattr(response, "data", None), "content", None)
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("GitHub Copilot returned an empty response.")
    return content.strip()


def chat(system: str, user: str, temperature: float = 0.1) -> tuple[str, dict[str, int]]:
    provider, github_token = _llm_context.get()
    if provider == "github_copilot":
        try:
            return asyncio.run(
                _chat_with_github_copilot(system, user, str(github_token))
            ), empty_usage()
        except Exception as exc:
            logger.exception("GitHub Copilot SDK request failed: %s", type(exc).__name__)
            raise RuntimeError(
                "GitHub Copilot request failed. Verify the saved token and Copilot access."
            ) from exc

    client, model = build_llm_client()
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )
    except Exception as first_err:
        if _vox_configured() and "401" in str(first_err):
            get_vox_access_token(force_refresh=True)
            client, model = build_llm_client()
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
            )
        else:
            raise

    text = (resp.choices[0].message.content or "").strip()
    return text, _usage_from_response(resp)
