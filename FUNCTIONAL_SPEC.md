# Scanstamp – Functional Specification

This document defines the **complete functional, behavioral, and UX requirements** for the Scanstamp command-line application.

It is the **authoritative contract** for behavior. Code must conform to this document.

---

## 1. Purpose and Scope

### Purpose

Scanstamp standardizes file naming by enforcing a canonical format:

```
YYYYMMDD - Document Name.ext
```

It optionally derives document titles by scanning file contents and invoking a Large Language Model (LLM), either via an external CLI (`sgpt`) or direct OpenAI API calls.

### Primary Use Cases

- Enforce date-prefixed filenames across document repositories
- Re-date existing documents without altering titles
- Rename documents based on content-derived titles (PDF, DOCX, text, etc.)
- Provide safe preview, confirmation, collision handling, logging, and undo

### Non-Goals

- No modification of file contents
- No cloud indexing or repository crawling
- No reliance on document metadata as authoritative

---

## 2. Definitions and Naming Rules

### Date Prefix Detection

A filename is considered “dated” if its stem matches:

```
^\d{8}\s*-\s*.+$
```

Example:

```
20251205 - Will of Clyde Ioerger.docx
```

Spacing around the hyphen may vary in input, but output **must normalize** to:

```
YYYYMMDD - Title
```

### Title Rules

When generating or normalizing titles:

- Title Case preferred
- Typical length: 4–12 words (configurable)
- No surrounding quotes
- No file extension
- Remove OS-invalid filename characters
- Collapse repeated whitespace
- Trim leading/trailing whitespace
- Remove control characters

### Output Filename Format

```
<date> - <title><original_extension>
```

---

## 3. Operating Modes

Exactly **one mode** is active per run.

Default mode: **smart-title**

### 3.1 Smart-Title Mode (Default)

- Extract text from file when feasible
- Build excerpt
- Ask LLM for *Document Name Only*
- Construct:
  ```
  YYYYMMDD - <LLM title>.<ext>
  ```

### 3.2 `--date-only`

- If filename already dated → skip
- Otherwise prepend date to existing stem
- Never scans file content
- Never calls LLM

### 3.3 `--redate`

- Replace existing date prefix if present
- Otherwise add date
- Preserve existing title portion
- Never calls LLM

### 3.4 `--keep-title`

- Replace or add date
- Preserve title exactly as-is
- Never calls LLM

### 3.5 `--keep-date`

- Smart-title only
- Preserve existing date if present
- Otherwise choose date per selection rules
- Title may still be replaced by LLM

### 3.6 Undo Mode: `--undo [FILE]`

- Reverse previous renames using log file
- Default log: `.scanstamp-log.csv`
- Supports `--dry-run`

---

## 4. Inputs, Targets, and Traversal

### Inputs

- Accepts one or more paths:
  - File
  - Directory
  - Shell-expanded glob
- If no paths supplied and not in undo mode → default to `.`

### Directory Handling

- Non-recursive by default
- Recursive traversal enabled with `--recursive`

### Filters

- `--include GLOB` (repeatable)
- `--exclude GLOB` (repeatable)

Glob behavior must work internally on all platforms, including Windows.

---

## 5. Date Selection Rules

### Priority Order

1. `--date YYYYMMDD`
2. `--use-mtime`
3. Default: today’s local date

### Optional: `--prefer-doc-date` (Smart Mode)

- Parse candidate dates from extracted text
- Supported formats:
  - `YYYY-MM-DD`
  - `YYYY/MM/DD`
  - `MM/DD/YYYY`
  - `Month DD, YYYY`
- Heuristic only; never errors if not found
- Ignored if explicit date override provided

---

## 6. Text Extraction and Excerpt Construction

### Supported Formats

| Type | Method |
|----|----|
| `.docx` | Unzip + parse `word/document.xml` |
| `.doc` | macOS: `textutil`; Windows: LibreOffice/antiword |
| `.txt`, `.md` | UTF-8 tolerant read |
| `.rtf` | macOS: `textutil`; others via library |
| `.pdf` | `pdftotext`; OCR fallback |

### OCR

- Enabled via `--ocr`
- Render first page → OCR with `tesseract`

### Unknown Formats

- No extraction
- Fall back based on active mode

### Excerpt Modes (`--excerpt-mode`)

- `firstline`
- `headings`
- `firstparas`
- `raw`

### Character Limit

- Controlled by `--chars N`
- Default: `1200`

---

## 7. LLM Integration

### Behavior

- LLM must return **one line only**
- First line is used
- All extra output discarded

### Prompt Contract

LLM must:
- Return title only
- No date, quotes, or extension
- Title Case
- Avoid invalid filename characters
- Fall back to existing title if excerpt is uninformative

### Security

- No plaintext key storage
- Support `OPENAI_API_KEY` env var

### Privacy Controls

- `--no-llm`
- `--local-only`

---

## 8. Rename Execution, Safety, and UX

### Preview

- `--dry-run` prints proposed changes only

### Confirmation

- Prompt per file by default
- `--yes` bypasses prompts
- `--confirm` forces prompts

### Collision Handling

- Default: skip
- `--suffix` appends `(2)`, `(3)`, etc.

### Failure Behavior

- Continue processing after failures
- Report per-file errors

---

## 9. Logging, Reporting, and Undo

### Log File

- Default: `.scanstamp-log.csv`
- Override: `--log FILE`

Format:
```
timestamp,action,old_path,new_path
```

### Report File

- Enabled via `--report FILE`

Format:
```
old_path,new_path,mode,status
```

### Undo

- Reverse in reverse order
- Skips missing/conflicting files
- Supports `--dry-run`

---

## 10. CLI Flags (Complete)

### Modes
- `--date-only`
- `--redate`
- `--keep-date`
- `--keep-title`

### Safety / UX
- `--confirm`
- `--yes`
- `--dry-run`
- `--undo [FILE]`
- `--log FILE`
- `--report FILE`

### Traversal
- `--recursive`
- `--include GLOB`
- `--exclude GLOB`

### Date
- `--date YYYYMMDD`
- `--use-mtime`
- `--prefer-doc-date`

### Extraction / Naming
- `--chars N`
- `--excerpt-mode`
- `--ocr`

### Collisions
- `--suffix`

### Standard
- `-h`, `--help`
- `--version`

---

## 11. Output Requirements

### Default Output

Rename:
```
Renamed: old.ext -> new.ext
```

Dry run:
```
DRY RUN: old.ext -> new.ext
```

Skip:
```
Already dated, skipping: name.ext
```

### Summary Block (Always Printed)

- Renamed count
- Skipped count
- Exists count
- Failed count
- Log path
- Report path (if any)

---

## 12. Cross-Platform Design

- Python implementation with PyInstaller
- Auto-detect optional tools
- Provide:
  ```
  scanstamp diagnose
  ```

---

## 13. Future Enhancements

- `--verbose`, `--quiet`
- `--json` output
- Model selection
- Redaction patterns
- Naming policy profiles
- Transaction / rollback mode
- Watch mode

---

## 14. Testing Requirements

### Unit Tests
- Date parsing
- Sanitization
- Mode behavior
- Collision handling
- Glob filtering

### Integration Tests
- DOCX/PDF extraction
- OCR fallback
- Windows path edge cases

### Acceptance Criteria
- Batch-safe execution
- Undo is reliable
- No path leakage without verbose

---

## 15. Security and Compliance

- No plaintext API keys
- Env var support for CI
- Explicit opt-in for OCR and LLM

---

## 16. Canonical Examples

Re-date everything (keep titles):
```bash
scanstamp --yes --keep-title --date 20251205 .
```

Add date to undated files only:
```bash
scanstamp --yes --date-only .
```

Smart-title DOCX only:
```bash
scanstamp --yes --excerpt-mode firstparas *.docx
```

Recursive excluding Archive:
```bash
scanstamp --yes --recursive --exclude "Archive" .
```

Dry-run with report:
```bash
scanstamp --report changes.csv --dry-run .
```

Undo:
```bash
scanstamp --undo
```
