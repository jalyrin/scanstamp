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

app = typer.Typer(add_completion=False)
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


@app.command()
def main(
    paths: List[FSPath] = typer.Argument(
        None,
        help="Files, directories, or globs. Defaults to current directory.",
    ),

    # Mode selection.
    date_only: bool = typer.Option(False, "--date-only"),
    redate: bool = typer.Option(False, "--redate"),
    keep_title: bool = typer.Option(False, "--keep-title"),
    keep_date: bool = typer.Option(False, "--keep-date"),

    # Safety and UX.
    confirm: bool = typer.Option(False, "--confirm"),
    yes: bool = typer.Option(False, "--yes"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    undo: Optional[FSPath] = typer.Option(None, "--undo"),
    log_path: FSPath = typer.Option(FSPath(DEFAULT_LOG_NAME), "--log"),
    report_path: Optional[FSPath] = typer.Option(None, "--report"),

    # Traversal.
    recursive: bool = typer.Option(False, "--recursive"),
    include: List[str] = typer.Option([], "--include"),
    exclude: List[str] = typer.Option([], "--exclude"),

    # Date selection.
    date: Optional[str] = typer.Option(None, "--date"),
    use_mtime: bool = typer.Option(False, "--use-mtime"),
    prefer_doc_date: bool = typer.Option(False, "--prefer-doc-date"),

    # Extraction and naming.
    chars: int = typer.Option(1200, "--chars"),
    excerpt_mode: ExcerptMode = typer.Option(ExcerptMode.firstparas, "--excerpt-mode"),
    ocr: bool = typer.Option(False, "--ocr"),

    # Collision handling.
    suffix: bool = typer.Option(False, "--suffix"),

    # Privacy and LLM control.
    no_llm: bool = typer.Option(False, "--no-llm"),
    local_only: bool = typer.Option(False, "--local-only"),

    version: bool = typer.Option(False, "--version"),
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


@app.command()
def diagnose():
    # Report availability of optional external dependencies.
    run_diagnose()


if __name__ == "__main__":
    app()
