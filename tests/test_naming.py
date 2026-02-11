# Unit tests for scanstamp.naming.
# These tests validate filename rules and date selection behavior.

from __future__ import annotations

from pathlib import Path

import pytest

from scanstamp.naming import (
    build_target_name,
    choose_date_prefix,
    is_dated_filename,
    sanitize_title,
)


def test_is_dated_filename_true_on_valid_prefix() -> None:
    assert is_dated_filename("20251205 - Will of Clyde Ioerger.docx") is True
    assert is_dated_filename("20251205-Title.pdf") is True
    assert is_dated_filename("20251205   -   Title.txt") is True


def test_is_dated_filename_false_on_missing_or_invalid_prefix() -> None:
    assert is_dated_filename("Will of Clyde Ioerger.docx") is False
    assert is_dated_filename("2025120 - Title.docx") is False
    assert is_dated_filename("202512051 - Title.docx") is False
    assert is_dated_filename("2025-12-05 - Title.docx") is False


def test_sanitize_title_removes_quotes_invalid_chars_and_normalizes_whitespace() -> None:
    raw = '  "hello: world  /  test"   '
    out = sanitize_title(raw, prefer_title_case=False)
    assert out == "hello world test"


def test_sanitize_title_title_cases_by_default_when_enabled() -> None:
    raw = "the quick brown fox"
    out = sanitize_title(raw, prefer_title_case=True)
    assert out == "The Quick Brown Fox"


def test_build_target_name_normalizes_hyphen_spacing() -> None:
    assert build_target_name("20260110", "Title", ".pdf") == "20260110 - Title.pdf"


def test_sanitize_title_preserves_possessive_apostrophes() -> None:
    out = sanitize_title("Dad's cheat sheet", prefer_title_case=True)
    assert out == "Dad's Cheat Sheet"


def test_choose_date_prefix_accepts_explicit_date() -> None:
    p = Path("any.txt")
    assert choose_date_prefix(p, explicit="20251205", use_mtime=False) == "20251205"


def test_choose_date_prefix_rejects_bad_explicit_date() -> None:
    p = Path("any.txt")
    with pytest.raises(ValueError):
        choose_date_prefix(p, explicit="2025-12-05", use_mtime=False)
    with pytest.raises(ValueError):
        choose_date_prefix(p, explicit="2025120", use_mtime=False)
