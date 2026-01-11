# Development Environment – Scanstamp

This document describes the **recommended development environment**, tooling, and conventions for working on the Scanstamp project.

It is intentionally opinionated to minimize friction and ambiguity.

---

## Supported Platforms

Scanstamp is developed and tested on:

- macOS (primary)
- Linux (Ubuntu/Debian)
- Windows 10/11 (PowerShell)

All tooling and commands in this document are cross-platform unless explicitly noted.

---

## Python Version

**Python 3.10+ is required.**

Recommended:
- Python 3.11 for local development
- Python 3.10 minimum for compatibility

Verify:

```bash
python --version
```

---

## Virtual Environment

Always use a virtual environment.

From the repo root:

```bash
python -m venv .venv
```

Activate:

- macOS / Linux:
  ```bash
  source .venv/bin/activate
  ```
- Windows:
  ```powershell
  .venv\Scripts\Activate.ps1
  ```

Upgrade pip:

```bash
python -m pip install -U pip
```

---

## Project Layout

The project uses a **modern `src/` layout**.

```
scanstamp/
├── pyproject.toml
├── README.md
├── FUNCTIONAL_SPEC.md
├── DEVELOPMENT_ENVIRONMENT.md
├── man/
│   └── scanstamp.1
└── src/
    └── scanstamp/
        ├── __init__.py
        ├── cli.py
        ├── core.py
        ├── extract.py
        ├── llm.py
        ├── logging_undo.py
        ├── naming.py
        └── traverse.py
```

Key points:
- All importable Python code lives under `src/`
- No path hacks (`sys.path.append`) are allowed
- Console entry point is defined in `pyproject.toml`

---

## Installation (Editable)

Install the project in editable mode:

```bash
python -m pip install -e .
```

Verify installation:

```bash
scanstamp --help
python -c "import scanstamp; print(scanstamp.__file__)"
```

The printed path **must** point to `src/scanstamp`.

---

## Dependency Management

All runtime dependencies are declared in:

```
pyproject.toml → [project.dependencies]
```

Development tools (pytest, ruff, mypy) may be added later under optional groups.

Do **not** rely on globally installed packages.

---

## External Tools (Optional)

Some functionality depends on external tools. These are **optional** and auto-detected.

| Tool | Purpose |
|----|----|
| `pdftotext` | PDF text extraction |
| `tesseract` | OCR fallback |
| `sgpt` | External LLM CLI |

Check availability:

```bash
scanstamp diagnose
```

Scanstamp must behave safely when these tools are missing.

---

## LLM Development

LLM usage is optional and explicitly controlled.

Rules:
- Never require an API key for basic operation
- Respect `--no-llm` and `--local-only`
- LLM output must be treated as untrusted input
- Only the **first line** of LLM output is used

Secrets:
- Use `OPENAI_API_KEY` for development
- Never commit API keys
- No plaintext key storage in repo

---

## Coding Conventions

- Python style: PEP 8
- Prefer explicit, readable code over cleverness
- Fail safely and continue batch execution
- No silent destructive operations

File responsibilities are intentionally narrow:
- `cli.py`: argument parsing and UX
- `core.py`: orchestration
- `naming.py`: filename/date logic
- `extract.py`: text extraction
- `llm.py`: model integration
- `logging_undo.py`: logging and undo
- `traverse.py`: filesystem traversal

---

## Testing (Planned)

Planned test categories:

- Unit tests
  - Date parsing
  - Filename sanitization
  - Mode behavior
- Integration tests
  - DOCX / PDF extraction
  - Windows path edge cases
- Acceptance tests
  - Batch safety
  - Undo reliability

Tests will live under:

```
tests/
```

---

## Build and Distribution (Planned)

Target distribution options:
- PyInstaller single-file binary
- Homebrew (macOS)
- Winget / MSI (Windows)

The `src/` layout is required for reliable builds.

---

## Versioning

Scanstamp follows semantic versioning:

```
MAJOR.MINOR.PATCH
```

- Breaking changes → MAJOR
- New features → MINOR
- Fixes → PATCH

---

## Development Rules (Non-Negotiable)

- No breaking CLI changes without updating FUNCTIONAL_SPEC.md
- No behavior changes without tests (once test suite exists)
- No undocumented flags
- Safety over convenience

---

## Status

Scanstamp is under active development.

This document defines the **authoritative development setup**.  
If behavior or tooling deviates from this document, the document must be updated.
