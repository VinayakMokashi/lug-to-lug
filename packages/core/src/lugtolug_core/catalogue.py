"""The catalogue: published references with a source for every value, and the measured
reference watches.

Storage is plain CSV in data/catalogue, so every addition is reviewable line by line:

- `sources.csv`: one row per source;
- `published.csv`: one row per reference. An empty cell is unknown, never guessed;
- `field-sources.csv`: the values whose source is not their row's main source;
- `reference.csv`: the reference watches, measured with calipers in three rounds.

load_catalogue() turns the first three into CatalogueEntry objects, the form the API
serves, and reports every problem at once rather than stopping at the first.
"""

from __future__ import annotations

import csv
from collections.abc import Iterator
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from lugtolug_core.contracts.catalogue import CatalogueEntry, Source
from lugtolug_core.standin import Appearance, Dimensions
from lugtolug_core.vocab import BezelType, CaseMaterial, CaseShape, ColourName, StrapType

SOURCE_COLUMNS = ("id", "kind", "publisher", "title", "url", "accessed", "archived_url")
LENGTH_FIELDS = (
    "case_diameter_mm",
    "case_length_mm",
    "bezel_diameter_mm",
    "dial_opening_mm",
    "lug_to_lug_mm",
    "thickness_mm",
    "lug_width_mm",
)
TERM_FIELDS = (
    "bezel_type",
    "case_material",
    "case_colour",
    "dial_colour",
    "strap_type",
    "crown_position",
)
PUBLISHED_COLUMNS = (
    "id",
    "brand",
    "model",
    "reference",
    "aliases",
    "source",
    "case_shape",
    *LENGTH_FIELDS,
    *TERM_FIELDS,
)
FIELD_SOURCE_COLUMNS = ("entry_id", "field", "source")
CITABLE = frozenset({"case_shape", *LENGTH_FIELDS, *TERM_FIELDS})


class CatalogueError(Exception):
    """The catalogue files break one or more rules; `problems` lists them all."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__(f"{len(problems)} problem(s) in the catalogue:\n" + "\n".join(problems))
        self.problems = problems


def tolerance_from_text(text: str) -> float:
    """The ± a published length carries, from the precision it is written with.

    Whole millimetres ("40") give ±0.5 and halves ("40.5") ±0.25. Anything finer
    ("39.7", "11.95") gives ±0.1, the floor for the variation between two watches of the
    same reference.
    """
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise ValueError(f"not a number: {text!r}") from None
    exponent = value.as_tuple().exponent
    if not isinstance(exponent, int):
        raise ValueError(f"not a finite number: {text!r}")
    if exponent >= 0:
        return 0.5
    if exponent == -1 and value % 1 == Decimal("0.5"):
        return 0.25
    return 0.1


def _rows(path: Path, columns: tuple[str, ...], problems: list[str]) -> Iterator[dict[str, str]]:
    """Rows of a CSV whose header must be exactly `columns`, with cells stripped."""
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if tuple(reader.fieldnames or ()) != columns:
            problems.append(f"{path.name}: the header must be {','.join(columns)}")
            return
        for row in reader:
            yield {key: (value or "").strip() for key, value in row.items()}


def _describe(error: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(p) for p in e['loc']) or 'row'}: {e['msg']}" for e in error.errors()
    )


def load_sources(path: Path, problems: list[str]) -> dict[str, Source]:
    sources: dict[str, Source] = {}
    for line, row in enumerate(_rows(path, SOURCE_COLUMNS, problems), start=2):
        where = f"{path.name} line {line}"
        if row["id"] in sources:
            problems.append(f"{where}: source {row['id']} is listed twice")
            continue
        try:
            sources[row["id"]] = Source.model_validate(
                {**row, "archived_url": row["archived_url"] or None}
            )
        except ValidationError as e:
            problems.append(f"{where}: {_describe(e)}")
    return sources


def _entry(
    row: dict[str, str], cited_by: dict[str, str], sources: dict[str, Source]
) -> dict[str, Any]:
    """The JSON form of one published.csv row, ready to validate as a CatalogueEntry."""

    def source_of(field: str) -> str:
        return cited_by.get(field, row["source"])

    entry: dict[str, Any] = {
        "entry_version": 1,
        "id": row["id"],
        "brand": row["brand"],
        "model": row["model"],
        "reference": row["reference"],
        "aliases": [a.strip() for a in row["aliases"].split(";") if a.strip()],
        "source": row["source"],
        "case_shape": {"value": row["case_shape"], "source": source_of("case_shape")},
    }
    for field in LENGTH_FIELDS:
        text = row[field]
        entry[field] = (
            {
                "value_mm": float(text),
                "tolerance_mm": tolerance_from_text(text),
                "source": source_of(field),
            }
            if text
            else None
        )
    for field in TERM_FIELDS:
        text = row[field]
        value: object = int(text) if field == "crown_position" and text.isdigit() else text
        entry[field] = {"value": value, "source": source_of(field)} if text else None

    cited = [row["source"]] + [
        source_of(f) for f in sorted(CITABLE) if row[f] and source_of(f) != row["source"]
    ]
    unique = list(dict.fromkeys(cited))
    entry["sources"] = [sources[s].model_dump(mode="json") for s in unique if s in sources]
    return entry


def load_catalogue(directory: Path) -> list[CatalogueEntry]:
    """Every published reference, validated and with its citations resolved.

    Raises CatalogueError listing every problem found in the files.
    """
    problems: list[str] = []
    sources = load_sources(directory / "sources.csv", problems)

    published_path = directory / "published.csv"
    rows = list(_rows(published_path, PUBLISHED_COLUMNS, problems))
    ids = [row["id"] for row in rows]

    overrides: dict[str, dict[str, str]] = {}
    for line, fs in enumerate(
        _rows(directory / "field-sources.csv", FIELD_SOURCE_COLUMNS, problems), start=2
    ):
        where = f"field-sources.csv line {line}"
        if fs["entry_id"] not in ids:
            problems.append(f"{where}: no entry {fs['entry_id']} in published.csv")
        elif fs["field"] not in CITABLE:
            problems.append(f"{where}: {fs['field']} is not a field that takes a citation")
        elif fs["source"] not in sources:
            problems.append(f"{where}: unknown source {fs['source']}")
        elif fs["field"] in overrides.setdefault(fs["entry_id"], {}):
            problems.append(f"{where}: {fs['entry_id']}.{fs['field']} is cited twice")
        else:
            overrides[fs["entry_id"]][fs["field"]] = fs["source"]

    entries: list[CatalogueEntry] = []
    used: set[str] = set()
    for line, row in enumerate(rows, start=2):
        where = f"published.csv line {line} ({row['id'] or 'no id'})"
        if ids.count(row["id"]) > 1:
            problems.append(f"{where}: the id is used more than once")
            continue
        if row["source"] not in sources:
            problems.append(f"{where}: unknown source {row['source']!r}")
            continue
        cited_by = overrides.get(row["id"], {})
        for field in cited_by:
            if not row[field]:
                problems.append(f"{where}: {field} has a citation but no value")
        try:
            entry = CatalogueEntry.model_validate(_entry(row, cited_by, sources))
        except (ValidationError, ValueError) as e:
            detail = _describe(e) if isinstance(e, ValidationError) else str(e)
            problems.append(f"{where}: {detail}")
            continue
        used.update(s.id for s in entry.sources)
        entries.append(entry)

    for source_id in sorted(set(sources) - used):
        problems.append(f"sources.csv: {source_id} is not cited by any entry")
    if problems:
        raise CatalogueError(problems)
    return entries


def entry_dimensions(entry: CatalogueEntry) -> tuple[Dimensions, Appearance]:
    """What a catalogue entry knows, ready for standin.build_spec()."""
    if entry.case_diameter_mm is None:
        raise ValueError(f"{entry.id}: no published case diameter, so no stand-in")

    def mm(field: str) -> float | None:
        cited = getattr(entry, field)
        return None if cited is None else float(cited.value_mm)

    dims = Dimensions(
        case_shape=entry.case_shape.value,
        case_diameter_mm=entry.case_diameter_mm.value_mm,
        case_length_mm=mm("case_length_mm"),
        bezel_diameter_mm=mm("bezel_diameter_mm"),
        dial_opening_mm=mm("dial_opening_mm"),
        lug_to_lug_mm=mm("lug_to_lug_mm"),
        thickness_mm=mm("thickness_mm"),
        lug_width_mm=mm("lug_width_mm"),
        crown_position=entry.crown_position.value if entry.crown_position else None,
    )
    look = Appearance(
        bezel_type=entry.bezel_type.value if entry.bezel_type else None,
        case_material=entry.case_material.value if entry.case_material else None,
        case_colour=entry.case_colour.value if entry.case_colour else None,
        dial_colour=entry.dial_colour.value if entry.dial_colour else None,
        strap_type=entry.strap_type.value if entry.strap_type else None,
    )
    return dims, look


# ---------------------------------------------------------------------------------------
# The reference watches (reference.csv): measurements only, never identity or ownership.

MEASURED_FIELDS = LENGTH_FIELDS
REFERENCE_COLUMNS = (
    "watch_id",
    "case_shape",
    *(c for f in MEASURED_FIELDS for c in (f, f.replace("_mm", "_range_mm"))),
    "bezel_type",
    "case_material",
    "case_colour",
    "dial_colour",
    "strap_type",
    "rounds",
)

_Length = Annotated[float, Field(gt=0, le=100)]
_Range = Annotated[float, Field(ge=0, le=5)]


class Measured(BaseModel):
    """The median of the readings and their range (largest minus smallest)."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    median_mm: _Length
    range_mm: _Range


class ReferenceWatch(BaseModel):
    """One reference watch: caliper medians over three rounds, and what it looks like."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    watch_id: Annotated[str, Field(pattern=r"^W[0-9]{2,3}$")]
    case_shape: CaseShape
    case_diameter_mm: Measured
    case_length_mm: Measured | None
    bezel_diameter_mm: Measured | None
    dial_opening_mm: Measured | None
    lug_to_lug_mm: Measured | None
    thickness_mm: Measured | None
    lug_width_mm: Measured | None
    bezel_type: BezelType
    case_material: CaseMaterial
    case_colour: ColourName
    dial_colour: ColourName
    strap_type: StrapType
    rounds: Annotated[int, Field(ge=1)]

    def dimensions(self) -> tuple[Dimensions, Appearance]:
        def median(m: Measured | None) -> float | None:
            return None if m is None else m.median_mm

        dims = Dimensions(
            case_shape=self.case_shape,
            case_diameter_mm=self.case_diameter_mm.median_mm,
            case_length_mm=median(self.case_length_mm),
            bezel_diameter_mm=median(self.bezel_diameter_mm),
            dial_opening_mm=median(self.dial_opening_mm),
            lug_to_lug_mm=median(self.lug_to_lug_mm),
            thickness_mm=median(self.thickness_mm),
            lug_width_mm=median(self.lug_width_mm),
        )
        look = Appearance(
            bezel_type=self.bezel_type,
            case_material=self.case_material,
            case_colour=self.case_colour,
            dial_colour=self.dial_colour,
            strap_type=self.strap_type,
        )
        return dims, look


def load_reference(path: Path) -> list[ReferenceWatch]:
    """The reference watches. Raises CatalogueError listing every problem found."""
    problems: list[str] = []
    watches: list[ReferenceWatch] = []
    seen: set[str] = set()
    for line, row in enumerate(_rows(path, REFERENCE_COLUMNS, problems), start=2):
        where = f"{path.name} line {line} ({row['watch_id'] or 'no id'})"
        if row["watch_id"] in seen:
            problems.append(f"{where}: the watch is listed twice")
            continue
        seen.add(row["watch_id"])
        data: dict[str, Any] = {
            k: row[k] for k in REFERENCE_COLUMNS if not k.endswith("_mm") and k != "rounds"
        }
        data["rounds"] = row["rounds"]
        for field in MEASURED_FIELDS:
            median, spread = row[field], row[field.replace("_mm", "_range_mm")]
            if bool(median) != bool(spread):
                problems.append(f"{where}: {field} needs both its median and its range")
                continue
            data[field] = {"median_mm": median, "range_mm": spread} if median else None
        try:
            watches.append(ReferenceWatch.model_validate(data))
        except ValidationError as e:
            problems.append(f"{where}: {_describe(e)}")
    if problems:
        raise CatalogueError(problems)
    return watches
