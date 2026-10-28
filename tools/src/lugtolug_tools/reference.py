"""Build data/catalogue/reference.csv from the private measuring sheets.

    uv run poe reference            # check, then write
    uv run poe reference --dry-run  # check only

Each watch is measured in three separate rounds (capture protocol §4). Its catalogue
value is the median of the readings, and their range (largest minus smallest) is the
measuring error. The watch list adds what each watch looks like. Its brand, model and
reference number are never read here, so they can't reach the repository.
"""

from __future__ import annotations

import csv
import io
import statistics
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, get_args

from pydantic import ValidationError

from lugtolug_core.catalogue import MEASURED_FIELDS, REFERENCE_COLUMNS, ReferenceWatch
from lugtolug_core.standin import build_spec, check_spec
from lugtolug_core.vocab import BezelType, CaseMaterial, CaseShape, ColourName, StrapType

MEASUREMENT_COLUMNS = ("round", "watch_id", *MEASURED_FIELDS, "notes")
APPEARANCE = {
    "case_shape": CaseShape,
    "bezel_type": BezelType,
    "case_material": CaseMaterial,
    "case_colour": ColourName,
    "dial_colour": ColourName,
    "strap_type": StrapType,
}

# A row with more cells than its header: usually a decimal comma, as in 12,3 for 12.3.
EXTRA_CELLS = "more cells than the header (a comma inside a value?)"


@dataclass(frozen=True)
class Spread:
    field: str
    watches: int
    median_range_mm: float
    largest_range_mm: float
    worst_watch: str


def _rows(path: Path, problems: list[str]) -> list[dict[str, str]]:
    rows = []
    with path.open(encoding="utf-8", newline="") as f:
        for line, row in enumerate(csv.DictReader(f), start=2):
            if None in row:
                problems.append(f"{path.name} line {line}: {EXTRA_CELLS}")
                continue
            rows.append({k: (v or "").strip() for k, v in row.items()})
    return rows


def build_reference(measurements: Path, watch_list: Path) -> tuple[list[ReferenceWatch], list[str]]:
    """The measured watches, and every problem found. Unmeasured watches are skipped."""
    problems: list[str] = []
    looks = {row["watch_id"]: row for row in _rows(watch_list, problems)}
    readings: dict[str, dict[str, dict[int, float]]] = {}
    for line, row in enumerate(_rows(measurements, problems), start=2):
        where = f"{measurements.name} line {line} ({row.get('watch_id', '')})"
        values = {f: row.get(f, "") for f in MEASURED_FIELDS}
        if not any(values.values()):
            continue  # not measured yet
        if not row.get("round", "").isdigit():
            problems.append(f"{where}: round must be 1, 2 or 3")
            continue
        per_field = readings.setdefault(row["watch_id"], {})
        for name, text in values.items():
            if not text:
                continue
            try:
                value = float(text)
            except ValueError:
                problems.append(f"{where}: {name} {text!r} is not a number")
                continue
            if not 0 < value <= 100:
                problems.append(f"{where}: {name} {value} mm is outside 0-100 mm")
                continue
            if int(row["round"]) in per_field.setdefault(name, {}):
                problems.append(f"{where}: {name} has two readings in round {row['round']}")
            per_field[name][int(row["round"])] = value

    watches: list[ReferenceWatch] = []
    for watch_id in sorted(readings):
        per_field = readings[watch_id]
        rounds = sorted({r for by_round in per_field.values() for r in by_round})
        data: dict[str, Any] = {"watch_id": watch_id, "rounds": len(rounds)}
        for name in MEASURED_FIELDS:
            by_round = per_field.get(name, {})
            if by_round and sorted(by_round) != rounds:
                problems.append(
                    f"{watch_id}: {name} is measured in rounds {sorted(by_round)} "
                    f"but the watch in rounds {rounds}"
                )
            mm = list(by_round.values())
            data[name] = (
                {
                    "median_mm": round(statistics.median(mm), 2),
                    "range_mm": round(max(mm) - min(mm), 2),
                }
                if mm
                else None
            )
        look = looks.get(watch_id)
        if look is None:
            problems.append(f"{watch_id}: measured but not in {watch_list.name}")
            continue
        for column, vocabulary in APPEARANCE.items():
            allowed = get_args(vocabulary)
            word = look.get(column, "")
            if word not in allowed:
                words = ", ".join(allowed)
                problems.append(f"{watch_id}: {column} {word!r} is not one of {words}")
            data[column] = word
        if data["case_shape"] == "round" and data["case_length_mm"] is not None:
            problems.append(f"{watch_id}: a round case has no separate case length")
        try:
            watch = ReferenceWatch.model_validate(data)
        except ValidationError as e:
            problems.append(f"{watch_id}: " + "; ".join(str(err["msg"]) for err in e.errors()))
            continue
        for rule in check_spec(build_spec(*watch.dimensions())):
            problems.append(f"{watch_id}: {rule} (check the readings)")
        if watch.rounds < 3:
            problems.append(f"{watch_id}: measured in {watch.rounds} round(s); three are needed")
        watches.append(watch)
    return watches, problems


def reference_csv(watches: Iterable[ReferenceWatch]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=REFERENCE_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for w in watches:
        row: dict[str, object] = {
            "watch_id": w.watch_id,
            "case_shape": w.case_shape,
            "bezel_type": w.bezel_type,
            "case_material": w.case_material,
            "case_colour": w.case_colour,
            "dial_colour": w.dial_colour,
            "strap_type": w.strap_type,
            "rounds": w.rounds,
        }
        for name in MEASURED_FIELDS:
            m = getattr(w, name)
            row[name] = "" if m is None else f"{m.median_mm:.2f}"
            row[name.replace("_mm", "_range_mm")] = "" if m is None else f"{m.range_mm:.2f}"
        writer.writerow(row)
    return buffer.getvalue()


def repeatability(watches: Iterable[ReferenceWatch]) -> list[Spread]:
    """How far apart the three rounds were, field by field: the measuring error."""
    spreads = []
    watches = list(watches)
    for name in MEASURED_FIELDS:
        ranges = [(getattr(w, name).range_mm, w.watch_id) for w in watches if getattr(w, name)]
        if ranges:
            worst = max(ranges)
            spreads.append(
                Spread(
                    field=name,
                    watches=len(ranges),
                    median_range_mm=round(statistics.median(r for r, _ in ranges), 3),
                    largest_range_mm=worst[0],
                    worst_watch=worst[1],
                )
            )
    return spreads
