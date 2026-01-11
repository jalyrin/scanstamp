# Filename parsing, date selection, and title sanitization for scanstamp.
# This module is pure logic and must remain side-effect free.
#
# Keeping this code isolated enables reliable unit testing.

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Optional


# A filename is considered dated if the *stem* matches this pattern.
# Output formatting always normalizes spacing to: YYYYMMDD - Title
DATE_PREFIX_RE = re.compile(r"^\d{8}\s*-\s*.+$")

# Characters rejected on Windows filenames.
# We also drop them on other platforms to keep names portable.
_INVALID_WIN_CHARS = set('<>:"/\\|?*')

# Control characters are never valid in filenames and can cause display issues.
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1F\x7F]")

# Whitespace normalization used for title cleanup.
_MULTISPACE_RE = re.compile(r"\s+")


def is_dated_filename(filename: str) -> bool:
    # Determine whether a filename already includes a date prefix.
    stem = Path(filename).stem
    return bool(DATE_PREFIX_RE.match(stem))


def choose_date_prefix(path: Path, explicit: Optional[str], use_mtime: bool) -> str:
    # Apply date selection priority:
    # 1) explicit override
    # 2) file mtime
    # 3) today's local date
    if explicit is not None:
        if not re.fullmatch(r"\d{8}", explicit):
            raise ValueError("--date must be YYYYMMDD")
        return explicit

    if use_mtime:
        dt = datetime.fromtimestamp(path.stat().st_mtime)
        return dt.strftime("%Y%m%d")

    return datetime.now().strftime("%Y%m%d")


def sanitize_title(title: str, prefer_title_case: bool) -> str:
    # Normalize a title into a safe, portable filename component.
    # This function must not add extensions or dates.
    t = title.strip()

    # Remove surrounding quotes because LLMs often add them.
    if (t.startswith('"') and t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
        t = t[1:-1].strip()

    # Drop control characters early to avoid weird terminal behavior.
    t = _CONTROL_CHARS_RE.sub("", t)

    # Remove characters that are invalid on common filesystems.
    t = "".join(ch for ch in t if ch not in _INVALID_WIN_CHARS)

    # Collapse internal whitespace to keep names consistent.
    t = _MULTISPACE_RE.sub(" ", t).strip()

    if prefer_title_case:
        # Title casing is a heuristic.
        # We keep it simple now and refine later if needed.
        t = t.title()

    return t


def build_target_name(date_prefix: str, title: str, suffix: str) -> str:
    # Construct the final output filename.
    # The hyphen spacing is normalized here regardless of input.
    return f"{date_prefix} - {title}{suffix}"
