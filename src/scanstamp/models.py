# Shared data models for scanstamp.
# Lives in its own module to avoid circular imports between cli and core.

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path as FSPath
from typing import List, Optional


class Mode(str, Enum):
    smart_title = "smart-title"
    date_only = "date-only"
    redate = "redate"
    keep_title = "keep-title"


class ExcerptMode(str, Enum):
    firstline = "firstline"
    headings = "headings"
    firstparas = "firstparas"
    raw = "raw"


@dataclass(frozen=True)
class Options:
    mode: Mode
    keep_date: bool

    confirm: bool
    yes: bool
    dry_run: bool

    recursive: bool
    include: List[str]
    exclude: List[str]

    date: Optional[str]
    use_mtime: bool
    prefer_doc_date: bool

    chars: int
    excerpt_mode: ExcerptMode
    ocr: bool

    suffix: bool

    no_llm: bool
    local_only: bool

    log_path: FSPath
    report_path: Optional[FSPath]
