"""Check the private watch list on its own, before anything has been measured.

    uv run poe watch-list

`poe reference` reads the list too, but only for watches that have measurements, so a
wrong word can sit there unnoticed until the measuring is done. This command checks
every row as soon as the list is written. Brand, model and reference number are checked
for being filled in and nothing more, and the report names watches only by their IDs.
"""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path

from lugtolug_tools import sheets
from lugtolug_tools.plan import WATCH
from lugtolug_tools.reference import APPEARANCE, appearance_problems

COLUMNS = ("watch_id", "brand", "model", "reference_number", *APPEARANCE, "notes")


@dataclass(frozen=True)
class ListReport:
    complete: list[str]
    blank: list[str]
    problems: list[str]
    notes: list[str]

    @property
    def ok(self) -> bool:
        return not self.problems

    def render(self) -> str:
        lines = [f"{len(self.complete)} watch(es) complete, {len(self.blank)} blank"]
        lines += [f"  problem {problem}" for problem in self.problems]
        lines += [f"  note {note}" for note in self.notes]
        return "\n".join(lines)


def check_watch_list(path: Path, planned: Collection[str] = ()) -> ListReport:
    """Every row of the list, and whether it covers the watches in the session plan."""
    if sheets.header(path) != COLUMNS:
        return ListReport([], [], [f"{path.name}: the header must be {','.join(COLUMNS)}"], [])
    complete: list[str] = []
    blank: list[str] = []
    problems: list[str] = []
    notes: list[str] = []
    seen: set[str] = set()
    names: dict[tuple[str, str], list[str]] = {}
    for line, row in sheets.rows(path, problems):
        watch_id = row["watch_id"]
        if not WATCH.match(watch_id):
            problems.append(f"{path.name} line {line}: watch_id {watch_id!r} is not like W01")
            continue
        if watch_id in seen:
            problems.append(f"{watch_id}: listed twice")
            continue
        seen.add(watch_id)
        if not any(row[column] for column in COLUMNS[1:]):
            blank.append(watch_id)
            continue
        found = [f"{watch_id}: {c} is empty" for c in ("brand", "model") if not row[c]]
        found += appearance_problems(watch_id, row)
        problems += found
        if not found:
            complete.append(watch_id)
        if not row["reference_number"]:
            notes.append(f"{watch_id}: no reference number")
        names.setdefault((row["brand"].casefold(), row["model"].casefold()), []).append(watch_id)

    for watch_ids in names.values():
        if len(watch_ids) > 1:
            same = ", ".join(watch_ids)
            notes.append(f"{same}: the same brand and model; if they share a case, split together")
    problems += [
        f"{watch_id}: in the session plan but not on the list"
        for watch_id in sorted(set(planned) - seen)
    ]
    if planned:
        extra = sorted(seen - set(planned))
        notes += [f"{watch_id}: not in the session plan" for watch_id in extra]
    return ListReport(complete, blank, problems, notes)
