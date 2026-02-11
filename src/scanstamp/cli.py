# Command-line interface definition for scanstamp.
# This file is responsible only for argument parsing, validation,
# and dispatch into core application logic.
#
# No filesystem mutation or business logic should live here.

from __future__ import annotations

from pathlib import Path as FSPath
from typing import List, Optional

import typer
from rich.console import Console

from scanstamp import __version__
from scanstamp.core import run_rename, run_undo, run_diagnose
from scanstamp.logging_undo import DEFAULT_LOG_NAME
from scanstamp.models import ExcerptMode, Mode, Options

app = typer.Typer(
    add_completion=False,
    help="Rename scanned documents with date-prefixed, LLM-generated descriptive titles.",
)
console = Console()


def _resolve_mode(date_only: bool, redate: bool, keep_title: bool) -> Mode:
    # Enforce exactly one active mode.
    active = [flag for flag, enabled in {
        "date-only": date_only,
        "redate": redate,
        "keep-title": keep_title,
    }.items() if enabled]

    if len(active) > 1:
        raise typer.BadParameter(
            f"Exactly one mode flag may be set; received: {', '.join(active)}"
        )

    if date_only:
        return Mode.date_only
    if redate:
        return Mode.redate
    if keep_title:
        return Mode.keep_title

    # Default mode.
    return Mode.smart_title


@app.command(help="Rename scanned documents with smart, date-prefixed titles.")
def main(
    paths: List[FSPath] = typer.Argument(
        None,
        help="Files, directories, or globs. Defaults to current directory.",
    ),

    # Mode selection.
    date_only: bool = typer.Option(
        False, "--date-only",
        help="Prepend date only; leave the existing filename intact.",
        rich_help_panel="Mode Selection",
    ),
    redate: bool = typer.Option(
        False, "--redate",
        help="Replace an existing date prefix with a new one.",
        rich_help_panel="Mode Selection",
    ),
    keep_title: bool = typer.Option(
        False, "--keep-title",
        help="Keep the current title but add a date prefix.",
        rich_help_panel="Mode Selection",
    ),
    keep_date: bool = typer.Option(
        False, "--keep-date",
        help="Keep the existing date prefix in smart-title mode.",
        rich_help_panel="Mode Selection",
    ),

    # Safety and UX.
    confirm: bool = typer.Option(
        False, "--confirm",
        help="Prompt for confirmation before each rename.",
        rich_help_panel="Safety & UX",
    ),
    yes: bool = typer.Option(
        False, "--yes",
        help="Skip all confirmation prompts.",
        rich_help_panel="Safety & UX",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run",
        help="Preview renames without making changes.",
        rich_help_panel="Safety & UX",
    ),
    undo: Optional[FSPath] = typer.Option(
        None, "--undo",
        help="Undo renames using the given log file.",
        rich_help_panel="Safety & UX",
    ),
    log_path: FSPath = typer.Option(
        FSPath(DEFAULT_LOG_NAME), "--log",
        help="Path for the undo/rename log file.",
        rich_help_panel="Safety & UX",
    ),
    report_path: Optional[FSPath] = typer.Option(
        None, "--report",
        help="Write a summary report to this path.",
        rich_help_panel="Safety & UX",
    ),

    # Traversal.
    recursive: bool = typer.Option(
        False, "--recursive",
        help="Recurse into subdirectories.",
        rich_help_panel="Traversal",
    ),
    include: List[str] = typer.Option(
        [], "--include",
        help="Only process files matching these patterns.",
        rich_help_panel="Traversal",
    ),
    exclude: List[str] = typer.Option(
        [], "--exclude",
        help="Skip files matching these patterns.",
        rich_help_panel="Traversal",
    ),

    # Date selection.
    date: Optional[str] = typer.Option(
        None, "--date",
        help="Use this date (YYYY-MM-DD) instead of auto-detecting.",
        rich_help_panel="Date Selection",
    ),
    use_mtime: bool = typer.Option(
        False, "--use-mtime",
        help="Fall back to file modification time for the date.",
        rich_help_panel="Date Selection",
    ),
    prefer_doc_date: bool = typer.Option(
        False, "--prefer-doc-date",
        help="Prefer the date found inside the document content.",
        rich_help_panel="Date Selection",
    ),

    # Extraction and naming.
    chars: int = typer.Option(
        1200, "--chars",
        help="Max characters to extract for title generation.",
        rich_help_panel="Extraction & Naming",
    ),
    excerpt_mode: ExcerptMode = typer.Option(
        ExcerptMode.firstparas, "--excerpt-mode",
        help="Strategy for extracting text (e.g. firstparas, full).",
        rich_help_panel="Extraction & Naming",
    ),
    ocr: bool = typer.Option(
        False, "--ocr",
        help="Use OCR to extract text from image-based documents.",
        rich_help_panel="Extraction & Naming",
    ),

    # Collision handling.
    suffix: bool = typer.Option(
        False, "--suffix",
        help="Append a numeric suffix to avoid filename collisions.",
        rich_help_panel="Collision Handling",
    ),

    # Privacy and LLM control.
    no_llm: bool = typer.Option(
        False, "--no-llm",
        help="Disable LLM title generation entirely.",
        rich_help_panel="Privacy & LLM",
    ),
    local_only: bool = typer.Option(
        False, "--local-only",
        help="Use only local models; never send data to remote APIs.",
        rich_help_panel="Privacy & LLM",
    ),

    version: bool = typer.Option(
        False, "--version",
        help="Show version and exit.",
    ),
):
    # Handle version early and exit cleanly.
    if version:
        console.print(__version__)
        raise typer.Exit(code=0)

    # Undo mode short-circuits all other behavior.
    if undo is not None:
        run_undo(
            log_path=undo if undo else FSPath(DEFAULT_LOG_NAME),
            dry_run=dry_run,
            yes=yes,
            confirm=confirm,
        )
        raise typer.Exit(code=0)

    mode = _resolve_mode(date_only, redate, keep_title)

    # keep-date is only meaningful in smart-title mode.
    if keep_date and mode is not Mode.smart_title:
        raise typer.BadParameter("--keep-date applies only to smart-title mode")

    # --yes always overrides confirmation prompting.
    if yes:
        confirm = False

    if not paths:
        paths = [FSPath(".")]

    opts = Options(
        mode=mode,
        keep_date=keep_date,

        confirm=confirm,
        yes=yes,
        dry_run=dry_run,

        recursive=recursive,
        include=include,
        exclude=exclude,

        date=date,
        use_mtime=use_mtime,
        prefer_doc_date=prefer_doc_date,

        chars=chars,
        excerpt_mode=excerpt_mode,
        ocr=ocr,

        suffix=suffix,

        no_llm=no_llm,
        local_only=local_only,

        log_path=log_path,
        report_path=report_path,
    )

    run_rename(paths=paths, opts=opts)


@app.command(help="Check availability of optional external dependencies.")
def diagnose():
    # Report availability of optional external dependencies.
    run_diagnose()


if __name__ == "__main__":
    app()
