"""Isolated .env lookup tests; no real credentials or provider calls."""

from pathlib import Path

import pytest

from verdict_router import config


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    monkeypatch.setattr(config, "_LOADED", False)
    for name in ("OPENAI_API_KEY", "OPENROUTER_API_KEY", "OLLAMA_BASE_URL", "PYTHON_DOTENV_DISABLED"):
        # Record even initially absent variables so dotenv's later writes are
        # undone when the fixture exits.
        monkeypatch.setenv(name, "")
        monkeypatch.delenv(name, raising=False)


def checkout(directory: Path) -> Path:
    source = directory / "python" / "src" / "verdict_router" / "config.py"
    source.parent.mkdir(parents=True)
    source.write_text("# source marker", encoding="utf-8")
    (directory / "python" / "pyproject.toml").write_text('[project]\nname="verdict-router"', encoding="utf-8")
    return source


@pytest.mark.parametrize("working_directory", [".", "python", "python/tests"])
def test_checkout_root_env_from_supported_working_directories(tmp_path, monkeypatch, working_directory):
    root = tmp_path / "repo"
    source = checkout(root)
    directory = root / working_directory
    directory.mkdir(parents=True, exist_ok=True)
    (root / ".env").write_text(
        "OPENAI_API_KEY=test-openai\nOPENROUTER_API_KEY=test-openrouter\nOLLAMA_BASE_URL=http://test-local\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "__file__", str(source))
    monkeypatch.chdir(directory)
    assert config.get_openai_key() == "test-openai"
    assert config.get_openrouter_key() == "test-openrouter"
    assert config.get_ollama_base_url() == "http://test-local"


def test_process_environment_overrides_file_values(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config, "__file__", str(tmp_path / "installed" / "config.py"))
    (tmp_path / ".env").write_text("OPENAI_API_KEY=test-file\n", encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY", "  test-process  ")
    assert config.get_openai_key() == "test-process"


def test_current_directory_env_wins_without_merging_root_file(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    source = checkout(root)
    (root / ".env").write_text("OPENAI_API_KEY=test-root\nOPENROUTER_API_KEY=test-root-router\n", encoding="utf-8")
    (root / "python" / ".env").write_text("OPENAI_API_KEY=test-local\n", encoding="utf-8")
    monkeypatch.setattr(config, "__file__", str(source))
    monkeypatch.chdir(root / "python")
    assert config.get_openai_key() == "test-local"
    assert config.get_openrouter_key() == ""


def test_installed_wheel_can_find_checkout_root_from_working_directory(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    checkout(root)
    (root / ".env").write_text("OPENAI_API_KEY=test-root\n", encoding="utf-8")
    monkeypatch.setattr(config, "__file__", str(tmp_path / "site-packages" / "verdict_router" / "config.py"))
    monkeypatch.chdir(root / "python")
    assert config.get_openai_key() == "test-root"


def test_editable_source_root_is_fallback_outside_checkout(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    source = checkout(root)
    (root / ".env").write_text("OPENAI_API_KEY=test-root\n", encoding="utf-8")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.setattr(config, "__file__", str(source))
    monkeypatch.chdir(elsewhere)
    assert config.get_openai_key() == "test-root"


def test_installed_package_does_not_load_unrelated_ancestor_env(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("OPENAI_API_KEY=test-unrelated\n", encoding="utf-8")
    working = tmp_path / "unrelated" / "work"
    working.mkdir(parents=True)
    monkeypatch.setattr(config, "__file__", str(tmp_path / "lib" / "site-packages" / "verdict_router" / "config.py"))
    monkeypatch.chdir(working)
    assert config.get_openai_key() == ""


def test_loads_only_once(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config, "__file__", str(tmp_path / "installed" / "config.py"))
    path = tmp_path / ".env"
    path.write_text("OPENAI_API_KEY=test-first\n", encoding="utf-8")
    assert config.get_openai_key() == "test-first"
    monkeypatch.delenv("OPENAI_API_KEY")
    path.write_text("OPENAI_API_KEY=test-second\n", encoding="utf-8")
    assert config.get_openai_key() == ""
