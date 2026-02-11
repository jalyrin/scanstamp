from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from scanstamp.llm import (
    LLMResult,
    _backend,
    _clean_title,
    derive_title_with_llm,
    llm_available,
)


# ---------------------------------------------------------------------------
# llm_available / _backend
# ---------------------------------------------------------------------------


def test_llm_available_with_api_key(monkeypatch):
    """When openai is importable and OPENAI_API_KEY is set, available is True."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    # Ensure openai is importable (mock it if not installed)
    import sys

    fake_openai = MagicMock()
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    assert llm_available() is True
    assert _backend() == "openai"


def test_llm_available_without_key_or_sgpt(monkeypatch):
    """With no API key and no sgpt on PATH, available is False."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("scanstamp.llm.shutil.which", lambda _: None)
    # Force openai import to fail
    import builtins

    real_import = builtins.__import__

    def _block_openai(name, *args, **kwargs):
        if name == "openai":
            raise ImportError("no openai")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _block_openai)
    assert llm_available() is False
    assert _backend() is None


def test_llm_available_sgpt_fallback(monkeypatch):
    """When openai is absent but sgpt is on PATH, backend is sgpt."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    import builtins

    real_import = builtins.__import__

    def _block_openai(name, *args, **kwargs):
        if name == "openai":
            raise ImportError("no openai")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _block_openai)
    monkeypatch.setattr("scanstamp.llm.shutil.which", lambda cmd: "/usr/local/bin/sgpt")
    assert llm_available() is True
    assert _backend() == "sgpt"


# ---------------------------------------------------------------------------
# derive_title_with_llm — empty excerpt
# ---------------------------------------------------------------------------


def test_derive_title_empty_excerpt_returns_fallback():
    result = derive_title_with_llm("", "My Fallback")
    assert result.title == "My Fallback"
    assert "empty excerpt" in result.raw


def test_derive_title_whitespace_excerpt_returns_fallback():
    result = derive_title_with_llm("   \n\t  ", "My Fallback")
    assert result.title == "My Fallback"


# ---------------------------------------------------------------------------
# derive_title_with_llm — OpenAI success
# ---------------------------------------------------------------------------


def test_derive_title_openai_success(monkeypatch):
    """Mock openai to return a canned title."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    fake_message = SimpleNamespace(content="Quarterly Budget Review Report")
    fake_choice = SimpleNamespace(message=fake_message)
    fake_response = SimpleNamespace(choices=[fake_choice])

    import sys

    mock_client = MagicMock()
    mock_client.return_value.chat.completions.create.return_value = fake_response

    fake_openai = MagicMock()
    fake_openai.OpenAI = mock_client
    monkeypatch.setitem(sys.modules, "openai", fake_openai)

    result = derive_title_with_llm("Q3 budget figures...", "budget")
    assert result.title == "Quarterly Budget Review Report"


# ---------------------------------------------------------------------------
# derive_title_with_llm — OpenAI failure falls back to sgpt
# ---------------------------------------------------------------------------


def test_derive_title_openai_failure_falls_back_to_sgpt(monkeypatch):
    """When OpenAI raises, sgpt is tried next."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    import sys

    # Make openai importable but raise on use
    fake_openai = MagicMock()
    fake_openai.OpenAI.return_value.chat.completions.create.side_effect = RuntimeError("API down")
    monkeypatch.setitem(sys.modules, "openai", fake_openai)

    monkeypatch.setattr("scanstamp.llm.shutil.which", lambda cmd: "/usr/local/bin/sgpt")

    fake_proc = SimpleNamespace(stdout="Sgpt Generated Title\n", returncode=0)
    monkeypatch.setattr("scanstamp.llm.subprocess.run", lambda *a, **kw: fake_proc)

    result = derive_title_with_llm("Some document text", "fallback")
    assert result.title == "Sgpt Generated Title"


# ---------------------------------------------------------------------------
# _clean_title — quote stripping and multi-line
# ---------------------------------------------------------------------------


def test_clean_title_strips_quotes():
    assert _clean_title('"My Great Title"') == "My Great Title"


def test_clean_title_strips_single_quotes():
    assert _clean_title("'My Great Title'") == "My Great Title"


def test_clean_title_takes_first_line():
    assert _clean_title("First Line\nSecond Line\nThird") == "First Line"


def test_clean_title_skips_blank_lines():
    assert _clean_title("\n\n  Actual Title \n") == "Actual Title"


def test_clean_title_empty():
    assert _clean_title("") == ""
    assert _clean_title("   \n  \n  ") == ""


# ---------------------------------------------------------------------------
# derive_title_with_llm — quoted/multi-line output from OpenAI
# ---------------------------------------------------------------------------


def test_derive_title_strips_quotes_and_extra_lines(monkeypatch):
    """OpenAI sometimes wraps output in quotes or adds explanation lines."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    raw_output = '"Annual Performance Review Summary"\n\nThis title captures the essence...'
    fake_message = SimpleNamespace(content=raw_output)
    fake_choice = SimpleNamespace(message=fake_message)
    fake_response = SimpleNamespace(choices=[fake_choice])

    mock_client = MagicMock()
    mock_client.return_value.chat.completions.create.return_value = fake_response

    import sys

    fake_openai = MagicMock()
    fake_openai.OpenAI = mock_client
    monkeypatch.setitem(sys.modules, "openai", fake_openai)

    result = derive_title_with_llm("Performance review document...", "fallback")
    assert result.title == "Annual Performance Review Summary"
    assert '"' not in result.title


# ---------------------------------------------------------------------------
# derive_title_with_llm — all backends fail
# ---------------------------------------------------------------------------


def test_derive_title_all_backends_fail_returns_fallback(monkeypatch):
    """When both openai and sgpt fail, the fallback title is returned."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    import sys

    fake_openai = MagicMock()
    fake_openai.OpenAI.return_value.chat.completions.create.side_effect = RuntimeError("boom")
    monkeypatch.setitem(sys.modules, "openai", fake_openai)

    monkeypatch.setattr("scanstamp.llm.shutil.which", lambda _: None)

    result = derive_title_with_llm("some text", "Original Name")
    assert result.title == "Original Name"
    assert "fallback" in result.raw
