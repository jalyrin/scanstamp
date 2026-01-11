# LLM integration boundary for scanstamp.
# This module isolates all model calls behind a minimal, testable surface.
#
# The rest of the codebase must treat LLM output as untrusted input.

from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class LLMResult:
    title: str
    raw: str


def llm_available() -> bool:
    # Report whether an LLM backend is available.
    # For now we only check for an API key because the implementation
    # is intentionally stubbed during early development.
    return bool(os.environ.get("OPENAI_API_KEY"))


def derive_title_with_llm(excerpt: str, fallback_title: str) -> LLMResult:
    # Derive a title from an excerpt using an LLM backend.
    # Contract:
    # - Return title only (no quotes, no date, no extension)
    # - One line only; ignore any extra output
    # - Fall back if excerpt is uninformative
    if not excerpt.strip():
        return LLMResult(title=fallback_title, raw="(fallback: empty excerpt)")

    # Stub behavior: use first non-empty line of input as a placeholder.
    # This keeps the rest of the pipeline functional while we implement
    # sgpt and OpenAI backends.
    for line in excerpt.splitlines():
        line = line.strip()
        if line:
            return LLMResult(title=line, raw="(stub)")
    return LLMResult(title=fallback_title, raw="(fallback: no usable lines)")
