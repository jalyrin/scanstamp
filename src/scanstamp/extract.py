# Text extraction and excerpt construction for scanstamp.
# This module converts files into short text excerpts suitable for
# title generation and heuristic date parsing.
#
# Extraction must never mutate inputs and must fail safely.

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class ExtractionResult:
    excerpt: str
    method: str
    error: Optional[str] = None


def extract_excerpt(
    path: Path,
    excerpt_mode: str,
    max_chars: int,
    ocr: bool,
) -> ExtractionResult:
    # Extract text from a file and return a bounded excerpt.
    # Unsupported formats return an empty excerpt and a method marker.
    suffix = path.suffix.lower()

    if suffix in (".txt", ".md"):
        return _extract_text_file(path, excerpt_mode, max_chars)

    # TODO: implement docx, pdf, rtf, doc per functional specification.
    # Keeping this as a stub allows the CLI to work without external tools.
    return ExtractionResult(excerpt="", method="unsupported")


def _extract_text_file(path: Path, excerpt_mode: str, max_chars: int) -> ExtractionResult:
    # Read a plain text file and build an excerpt according to excerpt_mode.
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return ExtractionResult(excerpt="", method="text", error=str(exc))

    text = text.strip()
    if not text:
        return ExtractionResult(excerpt="", method="text-empty")

    if excerpt_mode == "raw":
        excerpt = text
    elif excerpt_mode == "firstline":
        excerpt = text.splitlines()[0]
    else:
        # For plain text, headings/firstparas are approximated by the first chunk.
        excerpt = _first_paragraphs(text)

    excerpt = excerpt.strip()
    if len(excerpt) > max_chars:
        excerpt = excerpt[:max_chars].rstrip()

    return ExtractionResult(excerpt=excerpt, method="text")


def _first_paragraphs(text: str) -> str:
    # Return the first paragraph-like chunk from a text blob.
    # This keeps behavior stable without guessing formatting conventions.
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    return parts[0] if parts else text
