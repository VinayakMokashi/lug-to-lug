"""The catalogue files load into cited entries, and every broken rule is reported."""

from __future__ import annotations

from pathlib import Path

import pytest

from lugtolug_core.catalogue import (
    FIELD_SOURCE_COLUMNS,
    PUBLISHED_COLUMNS,
    REFERENCE_COLUMNS,
    SOURCE_COLUMNS,
    CatalogueError,
    entry_dimensions,
    load_catalogue,
    load_reference,
    tolerance_from_text,
)
from lugtolug_core.standin import build_spec, check_spec

DATA = Path(__file__).resolve().parents[3] / "data" / "catalogue"


@pytest.mark.parametrize(
    ("text", "tolerance"),
    [("40", 0.5), ("41", 0.5), ("40.5", 0.25), ("39.7", 0.1), ("40.0", 0.1), ("11.95", 0.1)],
)
def test_tolerance_follows_the_published_precision(text: str, tolerance: float) -> None:
    assert tolerance_from_text(text) == tolerance


@pytest.mark.parametrize("text", ["forty", "", "NaN", "Infinity"])
def test_tolerance_needs_a_finite_number(text: str) -> None:
    with pytest.raises(ValueError, match="number"):
        tolerance_from_text(text)


def test_the_committed_catalogue_loads() -> None:
    # Runs on every change, so a row that breaks a rule fails CI.
    entries = load_catalogue(DATA)
    watches = load_reference(DATA / "reference.csv")
    assert len({e.id for e in entries}) == len(entries)
    assert len({w.watch_id for w in watches}) == len(watches)
    for entry in entries:
        if entry.case_diameter_mm is not None:
            assert check_spec(build_spec(*entry_dimensions(entry))) == []
    for watch in watches:
        assert check_spec(build_spec(*watch.dimensions())) == []


def _write(path: Path, header: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    lines = [",".join(header)] + [",".join(row.get(c, "") for c in header) for row in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


SOURCES = [
    {
        "id": "S0001",
        "kind": "manufacturer",
        "publisher": "Examplebrand",
        "title": "Diver 1234.56",
        "url": "https://example.com/1234-56",
        "accessed": "2026-10-28",
    },
    {
        "id": "S0002",
        "kind": "review",
        "publisher": "Example Reviews",
        "title": "Diver review",
        "url": "https://example.org/review",
        "accessed": "2026-10-28",
    },
]
DIVER = {
    "id": "examplebrand-1234-56",
    "brand": "Examplebrand",
    "model": "Diver",
    "reference": "1234.56",
    "aliases": "The Diver; ED",
    "source": "S0001",
    "case_shape": "round",
    "case_diameter_mm": "40",
    "lug_to_lug_mm": "47.5",
    "thickness_mm": "12.1",
    "lug_width_mm": "20",
    "bezel_type": "rotating_insert",
    "case_material": "steel",
    "dial_colour": "black",
    "strap_type": "bracelet",
    "crown_position": "3",
}
DRESS = {
    "id": "examplebrand-77",
    "brand": "Examplebrand",
    "model": "Dress",
    "reference": "77",
    "source": "S0001",
    "case_shape": "square",
    "case_diameter_mm": "25.5",
    "case_length_mm": "33",
}


def _catalogue(
    tmp_path: Path,
    published: list[dict[str, str]],
    overrides: list[dict[str, str]] | None = None,
    sources: list[dict[str, str]] | None = None,
) -> Path:
    _write(tmp_path / "sources.csv", SOURCE_COLUMNS, SOURCES if sources is None else sources)
    _write(tmp_path / "published.csv", PUBLISHED_COLUMNS, published)
    _write(tmp_path / "field-sources.csv", FIELD_SOURCE_COLUMNS, overrides or [])
    return tmp_path


def test_rows_become_cited_entries(tmp_path: Path) -> None:
    override = {"entry_id": DIVER["id"], "field": "lug_to_lug_mm", "source": "S0002"}
    entries = load_catalogue(_catalogue(tmp_path, [DIVER, DRESS], [override]))
    diver, dress = entries

    assert diver.aliases == ["The Diver", "ED"]
    assert diver.case_diameter_mm is not None
    assert (diver.case_diameter_mm.value_mm, diver.case_diameter_mm.tolerance_mm) == (40, 0.5)
    assert diver.lug_to_lug_mm is not None
    assert diver.lug_to_lug_mm.source == "S0002"
    assert diver.lug_to_lug_mm.tolerance_mm == 0.25
    assert diver.thickness_mm is not None
    assert diver.thickness_mm.tolerance_mm == 0.1
    assert diver.dial_opening_mm is None  # unpublished stays unknown
    assert [s.id for s in diver.sources] == ["S0001", "S0002"]
    assert diver.crown_position is not None
    assert diver.crown_position.value == 3

    assert [s.id for s in dress.sources] == ["S0001"]
    spec = build_spec(*entry_dimensions(dress))
    assert spec.case.length_mm == 33
    assert "lugs.lug_to_lug_mm" in spec.assumed
    assert check_spec(spec) == []


def test_every_problem_is_reported_at_once(tmp_path: Path) -> None:
    rows = [
        {**DIVER, "case_diameter_mm": "forty"},
        {**DRESS, "id": "examplebrand-78", "source": "S0099"},
        {**DRESS, "id": "examplebrand-79", "case_shape": "oval"},
        {**DRESS, "id": "examplebrand-80", "crown_position": "3.5"},
        DRESS,
        DRESS,
    ]
    overrides = [
        {"entry_id": "nobody", "field": "lug_to_lug_mm", "source": "S0001"},
        {"entry_id": DIVER["id"], "field": "brand", "source": "S0001"},
        {"entry_id": DIVER["id"], "field": "bezel_diameter_mm", "source": "S0002"},
        {"entry_id": DIVER["id"], "field": "thickness_mm", "source": "S0404"},
    ]
    unused = {**SOURCES[1], "id": "S0003"}
    with pytest.raises(CatalogueError) as caught:
        load_catalogue(_catalogue(tmp_path, rows, overrides, [*SOURCES, unused]))
    problems = "\n".join(caught.value.problems)
    for expected in [
        "could not convert string to float: 'forty'",
        "unknown source 'S0099'",
        "case_shape.value",
        "crown_position.value",
        "the id is used more than once",
        "no entry nobody",
        "brand is not a field that takes a citation",
        "bezel_diameter_mm has a citation but no value",
        "unknown source S0404",
        "S0003 is not cited by any entry",
    ]:
        assert expected in problems
    assert len(caught.value.problems) >= 10


def test_a_wrong_header_is_reported(tmp_path: Path) -> None:
    folder = _catalogue(tmp_path, [DIVER])
    (folder / "sources.csv").write_text("id,url\nS0001,https://example.com\n", encoding="utf-8")
    with pytest.raises(CatalogueError, match=r"sources\.csv: the header must be"):
        load_catalogue(folder)


def test_no_stand_in_without_a_diameter(tmp_path: Path) -> None:
    folder = _catalogue(tmp_path, [{**DRESS, "case_diameter_mm": ""}], sources=SOURCES[:1])
    (entry,) = load_catalogue(folder)
    with pytest.raises(ValueError, match="no published case diameter"):
        entry_dimensions(entry)


WATCH = {
    "watch_id": "W01",
    "case_shape": "round",
    "case_diameter_mm": "39.95",
    "case_diameter_range_mm": "0.04",
    "lug_to_lug_mm": "47.62",
    "lug_to_lug_range_mm": "0.10",
    "thickness_mm": "12.31",
    "thickness_range_mm": "0.06",
    "lug_width_mm": "20.02",
    "lug_width_range_mm": "0.03",
    "bezel_type": "rotating_insert",
    "case_material": "steel",
    "case_colour": "silver",
    "dial_colour": "black",
    "strap_type": "bracelet",
    "rounds": "3",
}


def test_reference_watches_load_with_their_spread(tmp_path: Path) -> None:
    path = tmp_path / "reference.csv"
    _write(path, REFERENCE_COLUMNS, [WATCH])
    (watch,) = load_reference(path)
    assert watch.case_diameter_mm.median_mm == 39.95
    assert watch.case_diameter_mm.range_mm == 0.04
    assert watch.bezel_diameter_mm is None
    spec = build_spec(*watch.dimensions())
    assert spec.lugs.lug_to_lug_mm == 47.62
    assert check_spec(spec) == []


def test_reference_rows_are_checked(tmp_path: Path) -> None:
    path = tmp_path / "reference.csv"
    rows = [
        {**WATCH, "lug_width_range_mm": ""},
        {**WATCH, "watch_id": "W02", "case_shape": "oval"},
        {**WATCH, "watch_id": "W02"},
    ]
    _write(path, REFERENCE_COLUMNS, rows)
    with pytest.raises(CatalogueError) as caught:
        load_reference(path)
    problems = "\n".join(caught.value.problems)
    assert "lug_width_mm needs both its median and its range" in problems
    assert "case_shape" in problems
    assert "listed twice" in problems
