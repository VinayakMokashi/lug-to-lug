"""Read the private sheets, however they were saved.

The sheets are edited by hand, often in Excel, which saves a CSV in one of two ways:
"CSV UTF-8" starts the file with a byte order mark, which would become part of the first
column's name, and plain "CSV" uses the Windows code page, where an accented letter
isn't valid UTF-8. Excel also writes rows of empty cells where a row was once touched.
None of that changes what the sheet says, so all of it is read the same way.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

# A row with more cells than its header: usually a decimal comma, as in 12,3 for 12.3.
EXTRA_CELLS = "more cells than the header (a comma inside a value?)"


def _reader(path: Path) -> csv.DictReader[str]:
    data = path.read_bytes()
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("cp1252", errors="replace")
    return csv.DictReader(io.StringIO(text, newline=""))


def header(path: Path) -> tuple[str, ...]:
    return tuple(_reader(path).fieldnames or ())


def rows(path: Path, problems: list[str]) -> list[tuple[int, dict[str, str]]]:
    """Each row with its line in the file, cells stripped; empty rows are skipped."""
    found = []
    reader = _reader(path)
    for row in reader:
        if None in row:
            problems.append(f"{path.name} line {reader.line_num}: {EXTRA_CELLS}")
            continue
        cells = {key: (value or "").strip() for key, value in row.items()}
        if any(cells.values()):
            found.append((reader.line_num, cells))
    return found
