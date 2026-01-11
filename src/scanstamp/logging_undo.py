# Rename logging and undo support for scanstamp.
# This module owns all persistence related to rename history.
#
# The log format is append-only CSV to keep undo operations simple,
# auditable, and resilient to partial failures.

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console

DEFAULT_LOG_NAME = ".scanstamp-log.csv"

console = Console()


class LogWriter:
    # Append-only CSV writer for rename operations.
    # Each successful rename must be logged immediately.
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("a", newline="", encoding="utf-8")
        self._writer = csv.writer(self._fh)

    def write_rename(self, old_path: Path, new_path: Path) -> None:
        # Record a successful rename.
        # Timestamp is ISO-8601 for human readability and sortability.
        ts = datetime.now().isoformat(timespec="seconds")
        self._writer.writerow([ts, "rename", str(old_path), str(new_path)])
        self._fh.flush()

    def close(self) -> None:
        self._fh.close()


class ReportWriter:
    # Optional CSV report writer.
    # This is overwritten per run and is not used for undo.
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._fh)
        self._writer.writerow(["old_path", "new_path", "mode", "status"])

    def write(
        self,
        old_path: Path,
        new_path: Optional[Path],
        mode: str,
        status: str,
    ) -> None:
        self._writer.writerow(
            [
                str(old_path),
                str(new_path) if new_path else "",
                mode,
                status,
            ]
        )
        self._fh.flush()

    def close(self) -> None:
        self._fh.close()


def undo_from_log(
    log_path: Path,
    dry_run: bool,
    yes: bool,
    confirm: bool,
) -> None:
    # Reverse rename operations recorded in a log file.
    # Operations are processed in reverse order to maintain correctness.
    if not log_path.exists():
        raise FileNotFoundError(f"Undo log not found: {log_path}")

    rows = []
    with log_path.open("r", newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        for row in reader:
            if len(row) != 4:
                continue
            ts, action, old_path, new_path = row
            if action != "rename":
                continue
            rows.append((old_path, new_path))

    for old_str, new_str in reversed(rows):
        old = Path(old_str)
        new = Path(new_str)

        # Missing files are skipped silently to keep undo robust.
        if not new.exists():
            console.print(f"Missing, skipping undo: {new}")
            continue

        # Conflicts are never overwritten automatically.
        if old.exists():
            console.print(f"Conflict, skipping undo: {old}")
            continue

        if dry_run:
            console.print(f"DRY RUN UNDO: {new} -> {old}")
            continue

        if not yes:
            response = console.input(
                f"Undo rename?\n  {new}\n-> {old}\n[y/N]: "
            )
            if response.strip().lower() not in ("y", "yes"):
                console.print(f"Skipping undo: {new}")
                continue

        new.rename(old)
        console.print(f"Undone: {new} -> {old}")
