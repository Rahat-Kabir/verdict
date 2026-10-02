"""Environment / key loading.

Keys come from the process environment; as a convenience we also load the
repo-root .env file when present (python-dotenv). Keys are never logged.
"""

from __future__ import annotations

import os
from pathlib import Path


def _repository_root(directory: Path) -> Path | None:
    # Only recognize Verdict's source layout; an installed wheel's ancestors
    # must not be mistaken for a repository just because they contain .env.
    for candidate in (directory, *directory.parents):
        if (
            (candidate / "python" / "pyproject.toml").is_file()
            and (candidate / "python" / "src" / "verdict_router" / "config.py").is_file()
        ):
            return candidate
    return None


def _dotenv_candidates() -> list[Path]:
    current_directory = Path.cwd()
    candidates = [current_directory / ".env"]
    for root in (
        _repository_root(current_directory),
        _repository_root(Path(__file__).resolve().parent),
    ):
        if root is not None and root / ".env" not in candidates:
            candidates.append(root / ".env")
    return candidates


def _load_dotenv_once() -> None:
    global _LOADED
    if _LOADED:
        return
    _LOADED = True
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - dotenv is a hard dependency
        return
    for candidate in _dotenv_candidates():
        if candidate.is_file():
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


def get_cloudflare_account_id() -> str:
    _load_dotenv_once()
    return os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()


def get_cloudflare_token() -> str:
    _load_dotenv_once()
    return os.environ.get("CLOUDFLARE_AUTH_TOKEN", "").strip()
