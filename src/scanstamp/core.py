# Core orchestration logic for scanstamp.
# This file coordinates traversal, naming decisions, safety checks,
# logging, and undo integration.
#
# It intentionally contains no CLI parsing and no low-level extraction logic.

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Tuple

from rich.console import Console

from scanstamp.cli import Options, Mode
from scanstamp.logging_undo import LogWriter, ReportWriter, undo_from_log
from scanstamp.naming import (
    build_target_name,
    choose_date_prefix,
    is_dated_filename,
    sanitize_title,
)
from scanstamp.traverse import iter_target_files
from scanstamp.extract import extract_excerpt, ExtractionResult
from scanstamp.llm import derive_title_with_llm, llm_available

console = Console()


# Simple counters used for the mandatory summary block.
@dataclass
class Counters:
    renamed: int = 0
    skipped: int = 0
    exists: int = 0
    failed: int = 0


def run_diagnose() -> None:
    # Report availability of optional external tools.
    # Missing tools must never be fatal.
    from shutil import which

    console.print("[bold]Scanstamp diagnose[/bold]")
    console.print(f"pdftotext: {'OK' if which('pdftotext') else 'missing'}")
    console.print(f"tesseract: {'OK' if which('tesseract') else 'missing'}")
    console.print(f"sgpt: {'OK' if which('sgpt') else 'missing'}")
    console.print(f"LLM available: {'OK' if llm_available() else 'missing'}")


def run_undo(log_path: Path, dry_run: bool, yes: bool, confirm: bool) -> None:
    # Undo operations are delegated entirely to logging_undo.
    undo_from_log(
        log_path=log_path,
        dry_run=dry_run,
        yes=yes,
        confirm=confirm,
    )


def run_rename(paths: Iterable[Path], opts: Options) -> None:
    # Entry point for all rename operations.
    # This function is batch-safe and must never abort on a single failure.
    counters = Counters()

    log_writer = LogWriter(opts.log_path)
    report_writer = ReportWriter(opts.report_path) if opts.report_path else None

    targets = list(
        iter_target_files(
            paths=paths,
            recursive=opts.recursive,
            include=opts.include,
            exclude=opts.exclude,
        )
    )

    for path in targets:
        try:
            status = _process_one(path, opts, log_writer, report_writer)
            if status == "renamed":
                counters.renamed += 1
            elif status == "exists":
                counters.exists += 1
            elif status == "failed":
                counters.failed += 1
            else:
                counters.skipped += 1
        except Exception as exc:
            # Last-resort safety net.
            # We log and continue so a single bad file never kills a batch.
            counters.failed += 1
            console.print(f"[red]FAILED:[/red] {path} ({exc})")

    log_writer.close()
    if report_writer:
        report_writer.close()

    _print_summary(counters, opts)


def _process_one(
    path: Path,
    opts: Options,
    log_writer: LogWriter,
    report_writer: Optional[ReportWriter],
) -> str:
    # Handle a single file.
    # Returns a normalized status string for summary accounting.
    if not path.exists() or not path.is_file():
        _report(report_writer, path, None, opts, "skipped:not-a-file")
        return "skipped"

    old_name = path.name

    # Date-only mode skips already-dated files.
    if opts.mode is Mode.date_only and is_dated_filename(old_name):
        console.print(f"Already dated, skipping: {old_name}")
        _report(report_writer, path, None, opts, "skipped")
        return "skipped"

    date_prefix = choose_date_prefix(
        path,
        explicit=opts.date,
        use_mtime=opts.use_mtime,
    )

    # keep-date preserves an existing prefix in smart-title mode.
    if opts.keep_date and opts.mode is Mode.smart_title and is_dated_filename(old_name):
        date_prefix = old_name[:8]

    # Determine base title according to active mode.
    if opts.mode in (Mode.date_only, Mode.redate, Mode.keep_title):
        title = _existing_title(path)
    else:
        title = _smart_title(path, opts)

    final_title = sanitize_title(
        title,
        prefer_title_case=opts.mode is not Mode.keep_title,
    )

    new_name = build_target_name(
        date_prefix=date_prefix,
        title=final_title,
        suffix=path.suffix,
    )
    new_path = path.with_name(new_name)

    if new_path == path:
        _report(report_writer, path, new_path, opts, "skipped")
        return "skipped"

    # Collision handling.
    if new_path.exists():
        if not opts.suffix:
            console.print(f"Exists, skipping: {new_name}")
            _report(report_writer, path, new_path, opts, "exists")
            return "exists"

        # Append numeric suffix until a free name is found.
        i = 2
        while True:
            candidate = path.with_name(
                build_target_name(
                    date_prefix,
                    f"{final_title} ({i})",
                    path.suffix,
                )
            )
            if not candidate.exists():
                new_path = candidate
                break
            i += 1

    # Dry-run prints only.
    if opts.dry_run:
        console.print(f"DRY RUN: {old_name} -> {new_path.name}")
        _report(report_writer, path, new_path, opts, "renamed:dry-run")
        return "renamed"

    # Default behavior prompts per file unless --yes is set.
    if not opts.yes:
        if not _confirm_rename(old_name, new_path.name):
            _report(report_writer, path, new_path, opts, "skipped:user")
            return "skipped"

    path.rename(new_path)
    console.print(f"Renamed: {old_name} -> {new_path.name}")
    log_writer.write_rename(old_path=path, new_path=new_path)
    _report(report_writer, path, new_path, opts, "renamed")
    return "renamed"


def _existing_title(path: Path) -> str:
    # Extract the title portion from an existing filename.
    stem = path.stem
    if is_dated_filename(path.name):
        parts = stem.split("-", 1)
        return parts[1].strip() if len(parts) == 2 else stem
    return stem


def _smart_title(path: Path, opts: Options) -> str:
    # Derive a title using content extraction and optional LLM.
    extraction: ExtractionResult = extract_excerpt(
        path=path,
        excerpt_mode=opts.excerpt_mode.value,
        max_chars=opts.chars,
        ocr=opts.ocr,
    )

    # Respect privacy flags and missing LLM capability.
    if opts.no_llm or opts.local_only or not llm_available():
        return _existing_title(path)

    result = derive_title_with_llm(
        excerpt=extraction.excerpt,
        fallback_title=_existing_title(path),
    )
    return result.title or _existing_title(path)


def _confirm_rename(old: str, new: str) -> bool:
    # Prompt the user for confirmation.
    # Default is conservative: anything other than explicit yes aborts.
    response = console.input(f"Rename?\n  {old}\n-> {new}\n[y/N]: ")
    return response.strip().lower() in ("y", "yes")


def _report(
    report_writer: Optional[ReportWriter],
    old_path: Path,
    new_path: Optional[Path],
    opts: Options,
    status: str,
) -> None:
    if report_writer:
        report_writer.write(
            old_path=old_path,
            new_path=new_path,
            mode=opts.mode.value,
            status=status,
        )


def _print_summary(counters: Counters, opts: Options) -> None:
    # Mandatory summary block printed at end of every run.
    console.print()
    console.print("[bold]Summary[/bold]")
    console.print(f"Renamed: {counters.renamed}")
    console.print(f"Skipped: {counters.skipped}")
    console.print(f"Exists:  {counters.exists}")
    console.print(f"Failed:  {counters.failed}")
    console.print(f"Log:     {opts.log_path}")
    if opts.report_path:
        console.print(f"Report:  {opts.report_path}")
