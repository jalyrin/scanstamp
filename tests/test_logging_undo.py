# Unit tests for scanstamp.logging_undo undo behavior.
# These tests validate reverse-order undo and conservative conflict handling.

from __future__ import annotations

from pathlib import Path

from scanstamp.logging_undo import LogWriter, undo_from_log


def test_undo_from_log_dry_run_does_not_rename(tmp_path: Path) -> None:
    a = tmp_path / "a.txt"
    a.write_text("a", encoding="utf-8")
    b = tmp_path / "b.txt"

    log = tmp_path / ".scanstamp-log.csv"
    lw = LogWriter(log)
    a.rename(b)
    lw.write_rename(old_path=a, new_path=b)
    lw.close()

    undo_from_log(log_path=log, dry_run=True, yes=True, confirm=False)

    assert b.exists()
    assert not a.exists()


def test_undo_from_log_renames_back_when_safe(tmp_path: Path) -> None:
    a = tmp_path / "a.txt"
    a.write_text("a", encoding="utf-8")
    b = tmp_path / "b.txt"

    log = tmp_path / ".scanstamp-log.csv"
    lw = LogWriter(log)
    a.rename(b)
    lw.write_rename(old_path=a, new_path=b)
    lw.close()

    undo_from_log(log_path=log, dry_run=False, yes=True, confirm=False)

    assert a.exists()
    assert not b.exists()


def test_undo_from_log_skips_when_target_exists(tmp_path: Path) -> None:
    a = tmp_path / "a.txt"
    a.write_text("a", encoding="utf-8")
    b = tmp_path / "b.txt"

    log = tmp_path / ".scanstamp-log.csv"
    lw = LogWriter(log)
    a.rename(b)
    lw.write_rename(old_path=a, new_path=b)
    lw.close()

    a.write_text("conflict", encoding="utf-8")

    undo_from_log(log_path=log, dry_run=False, yes=True, confirm=False)

    assert a.exists()
    assert b.exists()
