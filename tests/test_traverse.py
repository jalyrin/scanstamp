# Unit tests for scanstamp.traverse.
# These tests validate include/exclude filtering and directory traversal.

from __future__ import annotations

from pathlib import Path

from scanstamp.traverse import iter_target_files


def test_iter_target_files_non_recursive_directory(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "b.pdf").write_text("b", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.txt").write_text("c", encoding="utf-8")

    got = sorted(
        p.name for p in iter_target_files([tmp_path], recursive=False, include=[], exclude=[])
    )
    assert got == ["a.txt", "b.pdf"]


def test_iter_target_files_recursive_directory(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.txt").write_text("c", encoding="utf-8")

    got = sorted(
        str(p.relative_to(tmp_path))
        for p in iter_target_files([tmp_path], recursive=True, include=[], exclude=[])
    )
    assert got == ["a.txt", "sub/c.txt"]


def test_iter_target_files_include_filter(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "b.pdf").write_text("b", encoding="utf-8")

    got = sorted(
        p.name for p in iter_target_files([tmp_path], recursive=False, include=["*.pdf"], exclude=[])
    )
    assert got == ["b.pdf"]


def test_iter_target_files_exclude_filter(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "b.pdf").write_text("b", encoding="utf-8")

    got = sorted(
        p.name for p in iter_target_files([tmp_path], recursive=False, include=[], exclude=["*.pdf"])
    )
    assert got == ["a.txt"]
