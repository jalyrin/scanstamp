# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Development environment

- Recommended local setup (from `README.md`):
  - Create and activate a virtualenv in the project root:
    - macOS/Linux: `python -m venv .venv && source .venv/bin/activate`
    - Windows: `python -m venv .venv && .venv\Scripts\activate`
  - Install in editable mode:
    - `python -m pip install -U pip`
    - `python -m pip install -e .`
  - After installation, the `scanstamp` CLI should be on `PATH`.

## Common commands

All commands assume you are in the project root with the virtualenv activated.

### Running the CLI during development

- Help and version:
  - `scanstamp --help`
  - `scanstamp --version`
- Typical flows (see `README.md` and `FUNCTIONAL_SPEC.md` for details):
  - Smart title (default mode): `scanstamp document.pdf`
  - Date-only (no content scanning/LLM): `scanstamp --date-only .`
  - Re-date, keep existing title: `scanstamp --redate --date 20251205 .`
  - Keep title verbatim with explicit date: `scanstamp --keep-title --date 20251205 .`
  - Dry-run preview: `scanstamp --dry-run .`
  - Non-interactive batch mode: `scanstamp --yes ...`
  - Undo last run: `scanstamp --undo`
  - Diagnostics for optional tools/LLM: `scanstamp diagnose`

### Tests

The test suite is configured but still being built out (see `pyproject.toml` and `FUNCTIONAL_SPEC.md`). Use these commands when tests are present:

- Run all tests (quiet mode configured via `pyproject.toml`):
  - `python -m pytest`
- Run tests in a specific file:
  - `python -m pytest tests/test_naming.py`
- Run a single test by name (using `-k` expression):
  - `python -m pytest -k "TestNaming and test_is_dated_filename"`

### Linting and type checking

Configured tools live in `pyproject.toml`.

- Ruff (linting/formatting checks):
  - Whole project: `ruff check src tests`
- Mypy (static type checking):
  - `python -m mypy src`

Adjust paths if new top-level packages or test directories are added.

## High-level architecture

### Overview

`scanstamp` is a small, layered CLI application. Behavior is defined by `FUNCTIONAL_SPEC.md`; runtime code is in `src/scanstamp`. The main layers are:

- **CLI boundary** (`scanstamp.cli`)
- **Core orchestration** (`scanstamp.core`)
- **Pure business logic modules** (`naming`, `traverse`, `extract`, `llm`, `logging_undo`)

The design keeps CLI parsing, side-effectful operations, and pure logic separate so that tests can target individual modules without invoking the full CLI.

### CLI layer (`scanstamp.cli`)

- Uses Typer to define the `scanstamp` command and subcommand `scanstamp diagnose`.
- Translates raw CLI flags into a single immutable `Options` dataclass that captures:
  - Mode selection (`Mode` enum: `smart-title` (default), `date-only`, `redate`, `keep-title`)
  - Safety/UX flags (`--confirm`, `--yes`, `--dry-run`, `--undo`, logging/report paths)
  - Traversal options (`--recursive`, `--include`, `--exclude`)
  - Date selection (`--date`, `--use-mtime`, `--prefer-doc-date` placeholder)
  - Extraction/naming parameters (`--chars`, `--excerpt-mode`, `--ocr`)
  - Collision/LLM behavior (`--suffix`, `--no-llm`, `--local-only`)
- Responsibilities:
  - Validate mutually exclusive modes via `_resolve_mode`.
  - Enforce `--keep-date` only in smart-title mode.
  - Handle `--version` and `--undo` early, then delegate:
    - `run_undo(...)` for undo
    - `run_rename(paths, opts)` for normal operation

### Core orchestration (`scanstamp.core`)

- Entry points used by the CLI:
  - `run_rename(paths, opts)` — main batch rename pipeline.
  - `run_undo(...)` — thin wrapper delegating to `logging_undo.undo_from_log`.
  - `run_diagnose()` — reports availability of external tools (`pdftotext`, `tesseract`, `sgpt`, LLM backend).
- `run_rename` responsibilities:
  - Discover target files via `traverse.iter_target_files` using CLI-specified traversal and glob filters.
  - For each file, call `_process_one` to compute the new name and perform the rename (or dry-run).
  - Track `Counters` for renamed / skipped / exists / failed and emit the required summary block, including log/report paths.
- `_process_one` pipeline:
  - Skip non-files early and report status via `_report` (into `ReportWriter`).
  - Enforce `date-only` semantics by skipping already-dated names.
  - Select date prefix using `naming.choose_date_prefix`, with optional reuse of existing prefix when `keep-date` is set.
  - Compute the **base title**:
    - For `date-only` / `redate` / `keep-title`: derive from existing filename via `_existing_title`.
    - For `smart-title`: call `_smart_title`, which delegates to `extract.extract_excerpt` and optionally `llm.derive_title_with_llm`.
  - Sanitize title via `naming.sanitize_title` (invalid chars, whitespace, optional Title Case).
  - Build candidate filename with `naming.build_target_name`.
  - Handle collisions:
    - If target exists and `--suffix` is not set → mark as `exists`.
    - If `--suffix` is set → append numeric `(<n>)` suffix until a free name is found.
  - Respect `--dry-run` (print only) and `--yes`/`--confirm` prompting.
  - On real rename, call `Path.rename`, log via `LogWriter.write_rename`, and optionally emit a report row via `_report`.

### Naming and date logic (`scanstamp.naming`)

- `is_dated_filename` — determines whether a filename already has a canonical `YYYYMMDD - Title`-style prefix using `DATE_PREFIX_RE` on the stem only.
- `choose_date_prefix` — implements the date-selection priority from the functional spec:
  1. Explicit `--date` (validated as `YYYYMMDD`)
  2. File mtime (`--use-mtime`)
  3. Today’s local date
- `sanitize_title` — central place for making titles safe and portable:
  - Strip surrounding quotes, remove control characters and characters invalid on Windows.
  - Collapse whitespace and optionally apply simple Title Case.
- `build_target_name` — produces the final `"<date> - <title><ext>"` string.

### Traversal and globbing (`scanstamp.traverse`)

- `iter_target_files(paths, recursive, include, exclude)` is the **only** place that walks the filesystem.
- Behavior:
  - Expands globs manually so CLI can accept un-expanded patterns on shells that don’t expand them.
  - For directories:
    - Non-recursive: uses `Path.iterdir` and yields only files.
    - Recursive: uses `os.walk`.
  - Inclusion/exclusion:
    - `_matches_any` checks both basename and full path string against `fnmatch` patterns.
    - `exclude` is applied before `include`; if `include` is set, files must match at least one include pattern.
- No renaming or logging occurs here; it only yields `Path` objects for `core`.

### Extraction (`scanstamp.extract`)

- Current implementation focuses on text-like files; richer extraction for DOCX/PDF/RTF is stubbed but specified in `FUNCTIONAL_SPEC.md`.
- `ExtractionResult` dataclass wraps the excerpt, method label, and optional error.
- `extract_excerpt(path, excerpt_mode, max_chars, ocr)`:
  - For `.txt` / `.md`: reads UTF-8 text and builds an excerpt according to `excerpt_mode` (`raw`, `firstline`, `firstparas`/`headings`).
  - For other suffixes: returns an empty excerpt with method `"unsupported"` as a non-fatal stub.
- Helper `_first_paragraphs` approximates paragraph-based excerpts by splitting on blank lines.

### LLM boundary (`scanstamp.llm`)

- `llm_available()` — currently reports availability based solely on the `OPENAI_API_KEY` environment variable (implementation is intentionally stubbed).
- `derive_title_with_llm(excerpt, fallback_title)`:
  - Implements the contract that LLM output is a single-line title with no date/extension.
  - For now, uses a stub: first non-empty line of the excerpt becomes the title; otherwise falls back to `fallback_title` with a marker in `raw`.
- All other modules treat this as an external, untrusted dependency; flags `--no-llm` and `--local-only` short-circuit its use in `core._smart_title`.

### Logging and undo (`scanstamp.logging_undo`)

- Centralizes all persistence around rename history and reporting.
- `DEFAULT_LOG_NAME` is `.scanstamp-log.csv` in the working directory.
- `LogWriter`:
  - Append-only CSV writer; each rename row is `[timestamp, "rename", old_path, new_path]`.
- `ReportWriter`:
  - Optional per-run CSV report; header is `["old_path", "new_path", "mode", "status"]`.
- `undo_from_log(log_path, dry_run, yes, confirm)`:
  - Reads the log, filters `"rename"` actions, and iterates them in reverse order.
  - Skips missing targets or conflicts, honors `dry_run` and interactive confirmation, and performs rename reversals.

### Package metadata (`scanstamp.__init__`)

- Minimal module exposing `__version__` (mirrors `pyproject.toml`).
- No functional code; all behavior lives in submodules described above.

## Specification source of truth

- `FUNCTIONAL_SPEC.md` is the authoritative behavioral contract for the CLI, covering:
  - Canonical filename format and title rules.
  - Supported operating modes and flags.
  - Traversal rules, date selection, extraction, LLM interaction, logging/undo, and cross-platform considerations.
- When making behavior changes, update both the implementation and `FUNCTIONAL_SPEC.md` to keep them in sync.