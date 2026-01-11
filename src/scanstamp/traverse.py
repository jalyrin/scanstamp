# Filesystem traversal and glob filtering for scanstamp.
# This module centralizes all path discovery logic so behavior is
# consistent across platforms, especially on Windows.
#
# No renaming or mutation is allowed here.

from __future__ import annotations

import fnmatch
import os
from pathlib import Path
from typing import Iterable, Iterator, List


def _matches_any(path: Path, patterns: List[str]) -> bool:
    # Check whether a path matches any of the provided glob patterns.
    # We test both the basename and the full path string to give users
    # flexible matching without platform-specific surprises.
    if not patterns:
        return True

    name = path.name
    full = str(path)

    for pat in patterns:
        if fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(full, pat):
            return True

    return False


def iter_target_files(
    paths: Iterable[Path],
    recursive: bool,
    include: List[str],
    exclude: List[str],
) -> Iterator[Path]:
    # Yield files from the provided paths according to traversal rules.
    # Directories are expanded; files are yielded as-is.
    for p in paths:
        # Expand glob patterns manually to support shells that do not.
        if any(ch in str(p) for ch in ("*", "?", "[")):
            for match in Path(".").glob(str(p)):
                yield from iter_target_files(
                    paths=[match],
                    recursive=recursive,
                    include=include,
                    exclude=exclude,
                )
            continue

        if p.is_dir():
            if recursive:
                for root, _, files in os.walk(p):
                    for name in files:
                        f = Path(root) / name
                        if exclude and _matches_any(f, exclude):
                            continue
                        if include and not _matches_any(f, include):
                            continue
                        yield f
            else:
                for f in p.iterdir():
                    if not f.is_file():
                        continue
                    if exclude and _matches_any(f, exclude):
                        continue
                    if include and not _matches_any(f, include):
                        continue
                    yield f
        else:
            if not p.is_file():
                continue
            if exclude and _matches_any(p, exclude):
                continue
            if include and not _matches_any(p, include):
                continue
            yield p
