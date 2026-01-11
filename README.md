# scanstamp

**scanstamp** is a cross-platform command-line tool that standardizes filenames by applying a date prefix and, optionally, generating a human-meaningful document title derived from file content.

Canonical format:

```
YYYYMMDD - Document Name.ext
```

It is designed for bulk operation, safety, undoability, and predictable behavior across macOS, Windows, and Linux.

---

## Features

- Enforces date-prefixed filenames
- Smart title generation from document content (PDF, DOCX, text, etc.)
- Multiple operating modes (date-only, re-date, keep title, smart title)
- Dry-run preview and per-file confirmation
- Collision handling with optional suffixing
- CSV logging and full undo support
- Cross-platform globbing and traversal
- Explicit privacy controls (disable LLM, local-only operation)

---

## Installation (development)

Clone the repo and install in editable mode:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install -U pip
python -m pip install -e .
```

Verify:

```bash
scanstamp --help
scanstamp --version
```

---

## Basic Usage

### Smart title (default mode)

Derive a title from document content and apply today’s date:

```bash
scanstamp document.pdf
```

### Date-only (no content scanning, no LLM)

Add a date prefix only if missing:

```bash
scanstamp --date-only .
```

### Re-date existing files

Replace or add a date prefix, keep the existing title:

```bash
scanstamp --redate --date 20251205 .
```

### Keep title exactly as-is

```bash
scanstamp --keep-title --date 20251205 .
```

---

## Safety and Preview

Preview changes without renaming:

```bash
scanstamp --dry-run .
```

Skip prompts (dangerous for large batches):

```bash
scanstamp --yes .
```

---

## Undo

All renames are logged to `.scanstamp-log.csv` by default.

Undo the most recent run:

```bash
scanstamp --undo
```

Dry-run undo:

```bash
scanstamp --undo --dry-run
```

---

## Traversal and Filtering

Recursive traversal:

```bash
scanstamp --recursive .
```

Include / exclude globs (repeatable):

```bash
scanstamp --include "*.pdf" --exclude "Archive*" .
```

Globs work consistently on all platforms, including Windows.

---

## Date Selection

Priority order:

1. `--date YYYYMMDD`
2. `--use-mtime`
3. Today’s local date (default)

Example:

```bash
scanstamp --use-mtime report.docx
```

---

## Privacy and LLM Control

Disable all LLM usage:

```bash
scanstamp --no-llm
```

Force local-only behavior:

```bash
scanstamp --local-only
```

When LLMs are disabled, scanstamp falls back to existing filenames.

---

## Logging and Reporting

Default log file:

```
.scanstamp-log.csv
```

Custom log path:

```bash
scanstamp --log mylog.csv .
```

Generate a report CSV:

```bash
scanstamp --report changes.csv .
```

---

## Diagnostics

Check availability of optional external tools:

```bash
scanstamp diagnose
```

---

## Project Status

This project is under active development.

Implemented:
- CLI surface and modes
- Traversal, filtering, collision handling
- Logging and undo
- Safe rename workflow

In progress:
- Full DOCX / PDF / OCR extraction
- LLM backends (OpenAI API / sgpt)
- Test suite and CI

See `FUNCTIONAL_SPEC.md` for the complete design contract.

---

## License

MIT (see `pyproject.toml`)
