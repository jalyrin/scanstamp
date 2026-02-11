# LLM integration boundary for scanstamp.
# This module isolates all model calls behind a minimal, testable surface.
#
# The rest of the codebase must treat LLM output as untrusted input.

from __future__ import annotations

from dataclasses import dataclass
import os
import shutil
import subprocess

from rich.console import Console

_err = Console(stderr=True)

SYSTEM_PROMPT = (
    "You are a document title generator. Given a text excerpt from a file, return a single "
    "short document title (4-12 words, Title Case). Return ONLY the title on one line. "
    "No dates, no file extensions, no quotes, no explanation. "
    "If the text is uninformative, return the fallback title provided."
)


@dataclass(frozen=True)
class LLMResult:
    title: str
    raw: str


def _backend() -> str | None:
    """Return the best available backend name, or None."""
    try:
        import openai as _openai  # noqa: F401

        if os.environ.get("OPENAI_API_KEY"):
            return "openai"
    except ImportError:
        pass
    if shutil.which("sgpt"):
        return "sgpt"
    return None


def llm_available() -> bool:
    """Report whether any LLM backend is reachable."""
    return _backend() is not None


def _call_openai(excerpt: str, fallback_title: str) -> str:
    """Call the OpenAI chat API and return the raw response text."""
    import openai

    client = openai.OpenAI()
    user_message = (
        f"Excerpt:\n{excerpt}\n\nFallback title: {fallback_title}"
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=60,
        temperature=0.3,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )
    return response.choices[0].message.content or ""


def _call_sgpt(excerpt: str, fallback_title: str) -> str:
    """Call the sgpt CLI and return the raw response text."""
    prompt = (
        f"{SYSTEM_PROMPT}\n\nExcerpt:\n{excerpt}\n\nFallback title: {fallback_title}"
    )
    result = subprocess.run(
        ["sgpt", "--no-cache", prompt],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout or ""


def _clean_title(raw: str) -> str:
    """Extract and sanitize the first line of LLM output."""
    for line in raw.splitlines():
        line = line.strip().strip('"').strip("'").strip()
        if line:
            return line
    return ""


def derive_title_with_llm(excerpt: str, fallback_title: str) -> LLMResult:
    """Derive a title from an excerpt using an LLM backend.

    Contract:
    - Return title only (no quotes, no date, no extension)
    - One line only; ignore any extra output
    - Fall back if excerpt is uninformative
    """
    if not excerpt.strip():
        return LLMResult(title=fallback_title, raw="(fallback: empty excerpt)")

    # Try OpenAI first.
    try:
        import openai as _openai  # noqa: F401

        if os.environ.get("OPENAI_API_KEY"):
            raw = _call_openai(excerpt, fallback_title)
            title = _clean_title(raw)
            if title:
                return LLMResult(title=title, raw=raw)
    except Exception as exc:
        _err.print(f"[dim]scanstamp: OpenAI error, trying sgpt: {exc}[/dim]")

    # Fall back to sgpt.
    try:
        if shutil.which("sgpt"):
            raw = _call_sgpt(excerpt, fallback_title)
            title = _clean_title(raw)
            if title:
                return LLMResult(title=title, raw=raw)
    except Exception as exc:
        _err.print(f"[dim]scanstamp: sgpt error: {exc}[/dim]")

    return LLMResult(title=fallback_title, raw="(fallback: all backends failed)")
