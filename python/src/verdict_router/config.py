"""Environment / key loading.

Keys come from the process environment; as a convenience we also load the
repo-root .env file when present (python-dotenv). Keys are never logged.
"""

from __future__ import annotations

import os
from pathlib import Path


def _load_dotenv_once() -> None:
    global _LOADED
    if _LOADED:
        return
    _LOADED = True
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - dotenv is a hard dependency
        return
    for candidate in (Path.cwd() / ".env", Path(__file__).resolve().parents[3] / ".env"):
        if candidate.exists():
            load_dotenv(candidate, override=False)
            return


_LOADED = False


def get_openai_key() -> str:
    _load_dotenv_once()
    return os.environ.get("OPENAI_API_KEY", "").strip()


def get_openrouter_key() -> str:
    _load_dotenv_once()
    return os.environ.get("OPENROUTER_API_KEY", "").strip()


def get_ollama_base_url() -> str:
    _load_dotenv_once()
    return os.environ.get("OLLAMA_BASE_URL", "").strip()
